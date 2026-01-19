import datetime
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction # Renamed to avoid conflict with model
from django.db.models import F

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Service, Transaction
from .serializers import (
    UserTransactionSerializer, 
    GuestTransactionSerializer,
    UserServiceSerializer,
    WalletHistorySerializer,
    ServiceHistorySerializer
)
from .utils import get_kashier_auth_headers, place_sickw_order, sync_services_if_expired

User = get_user_model()

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    
    def get_serializer_class(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return UserTransactionSerializer
        return GuestTransactionSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'kashier_webhook', 'show_order']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
  
        user = request.user if request.user.is_authenticated else None
        
        # Save transaction (Serializer handles atomic locks for "Wallet Spending")
        txn = serializer.save(user=user)
        
        # --- PATH A: REGISTERED USER (Wallet Balance) ---
        if txn.status == 'COMPLETED':
            
            place_sickw_order(txn)
            
            # [REMOVED: Email logic for registered users deleted as requested]
            
            user.refresh_from_db()
            txn.refresh_from_db()
            
            return Response({
                "transaction_id": txn.id,
                "transaction_status": txn.status,
                "api_result": txn.service_details.get('api_result'),
                "new_balance": float(user.balance),
            }, status=status.HTTP_201_CREATED)
            
        # --- PATH B: GUEST / TOPUP (Kashier Payment) ---
        
        # [Optimization] Don't hardcode localhost. Use dynamic base URL or settings.
        base_url = getattr(settings, 'BASE_URL', f"{request.scheme}://{request.get_host()}")
        frontend_url = "http://158.220.126.228:3000"
       
        redirect_url = f"{frontend_url}/"

        # [Optimization] Use settings for the webhook URL to avoid ngrok issues in production
        webhook_url = getattr(settings, 'KASHIER_WEBHOOK_URL', f"{base_url}/store/transactions/webhook/kashier/")

        # Extract Email safely
        guest_email = txn.guest_email if txn.guest_email else ""

        payload = {
            "expireAt": (datetime.datetime.now() + datetime.timedelta(minutes=30)).isoformat() + "Z",
            "maxFailureAttempts": 3,
            "amount": str(txn.amount),
            "currency": "EGP",
            "merchantId": settings.KASHIER_MID,
            "order": str(txn.merchant_transaction_id),
            "merchantRedirect": redirect_url, 
            "display": "en",
            "paymentType": "card",
            "serverWebhook": webhook_url,
            "type": "external",
            "allowedMethods": "card,wallet,fawry,instapay,basata",
            "customer": {
                "name": str(user.phone_number) if user else "Guest",
                "email": None if user else guest_email, # 👇 Sends Guest Email to Kashier (Safe to keep)
                "reference": str(user.id) if user else "guest"
            }
        }

        try:
            # [Optimization] Use a timeout to prevent hanging if Kashier is down
            response = requests.post(
                f"{settings.KASHIER_API_URL}/v3/payment/sessions",
                json=payload,
                headers=get_kashier_auth_headers(),
                timeout=10 
            )
            response.raise_for_status() # Raise error for 4xx/5xx codes
            
            response_data = response.json()
            payment_url = response_data.get('sessionUrl')
                
            if payment_url:
                kashier_id = response_data.get('_id') or response_data.get('kashierOrderId')
                if kashier_id:
                    txn.kashier_session_id = kashier_id
                    txn.save(update_fields=['kashier_session_id'])
                        
                return Response({
                    "status": "success",
                    "paymentUrl": payment_url, 
                    "transaction_id": txn.id,
                    "merchant_transaction_id": str(txn.merchant_transaction_id)
                }, status=status.HTTP_201_CREATED)
                
            # If no URL returned
            txn.status = 'FAILED'
            txn.save(update_fields=['status'])
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)  
            
        except requests.exceptions.RequestException as e:
            txn.status = 'FAILED'
            txn.save(update_fields=['status'])
            return Response({"error": f"Payment Gateway Error: {str(e)}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
    @action(detail=False, methods=['post'], url_path='webhook/kashier')
    def kashier_webhook(self, request):
        webhook_data = request.data.get('data', {})
        event_type = request.data.get('event')
        transaction_id = webhook_data.get('merchantOrderId')
        payment_status = webhook_data.get('status')
        kashier_txn_id = webhook_data.get('transactionId')
        
        if not transaction_id:
            return Response({"error": "No Order ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        # [Safety] Atomic block ensures status update + balance update happen together
        with db_transaction.atomic():
            try:
                # Lock the row to prevent simultaneous webhook updates
                txn = Transaction.objects.select_for_update().get(merchant_transaction_id=transaction_id)
            except Transaction.DoesNotExist:
                return Response({"error": "Not Found"}, status=status.HTTP_404_NOT_FOUND)

            # --- HANDLE REFUND ---
            if event_type == 'refund':
                if txn.status != 'REFUNDED':
                    txn.status = 'REFUNDED'
                    txn.save(update_fields=['status'])
                return Response({"status": "refund_processed"}, status=status.HTTP_200_OK)

            # --- HANDLE DUPLICATE ---
            if txn.status == 'COMPLETED':
                 return Response({"status": "already_processed"}, status=status.HTTP_200_OK)
            
            # --- HANDLE SUCCESS ---
            if payment_status == "SUCCESS":
                txn.status = 'COMPLETED'
                
                if kashier_txn_id:
                    txn.kashier_transaction_id = kashier_txn_id 
                if 'orderId' in webhook_data:
                    txn.kashier_session_id = webhook_data['orderId']
                
                txn.save() 
                
                # 1. BALANCE TOP-UP
                if txn.is_balance_topup and txn.user:
                    # [Safety] Use F() expressions for atomic addition.
                    # This prevents race conditions if two webhooks fire at once.
                    txn.user.balance = F('balance') + txn.amount
                    txn.user.save(update_fields=['balance'])
                    txn.user.refresh_from_db() # Reload to get clean number (optional)

                # 2. ORDER SERVICE (Direct Pay)
                elif txn.service_details and event_type != 'refund':
                    # A. Place the order
                    place_sickw_order(txn)
                    
                    # B. Reload to get the result Sickw just put in the DB
                    txn.refresh_from_db() 
                    
                    # 👇 FIX: Fetch the Real Service Name
                    from .models import Service
                    service_id = txn.service_details.get('service_id')
                    
                    # Try to find the service in DB to get its proper name
                    service_obj = Service.objects.filter(service_id=service_id).first()
                    if service_obj:
                        service_name = service_obj.name
                    else:
                        service_name = txn.service_details.get('service_name', f'Service #{service_id}')

                    # 👇 C. HANDLE EMAILS (Both Confirmation & Instant Result)
                    if txn.guest_email:
                        from .utils import send_guest_confirmation_email, send_guest_result_email
                        
                        # 1. Always send Confirmation
                        send_guest_confirmation_email(
                            txn.guest_email, 
                            txn.merchant_transaction_id, 
                            service_name
                        )

                        # 2. CHECK FOR INSTANT RESULT
                        api_result = txn.service_details.get('api_result', {})
                        
                        # Parse result text safely
                        if isinstance(api_result, dict):
                            result_text = api_result.get('result', '')
                        else:
                            result_text = str(api_result)

                        # If it is NOT Pending (meaning it is Instant Success), send the 2nd email NOW.
                        if result_text and "Pending" not in str(result_text) and "Process" not in str(result_text):
                            send_guest_result_email(
                                txn.guest_email,
                                txn.merchant_transaction_id,
                                service_name,
                                result_text
                            )
                    
            else:
                txn.status = 'FAILED'
                txn.save(update_fields=['status'])

        return Response({"status": "received"}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='show-order')
    def show_order(self, request):
        merchant_tx_id = request.query_params.get('merchant_transaction_id')
        if not merchant_tx_id:
            return Response({"error": "merchant_transaction_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            txn = Transaction.objects.get(merchant_transaction_id=merchant_tx_id)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = GuestTransactionSerializer(txn)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='wallet-history')
    def wallet_history(self, request):
 
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        transactions = Transaction.objects.filter(user=user).order_by('-created_at')
        
      
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = WalletHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = WalletHistorySerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='service-history')
    def service_history(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
           
        transactions = Transaction.objects.filter(
            user=user, 
            is_balance_topup=False
        ).order_by('-created_at')
        
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = ServiceHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = ServiceHistorySerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='test-sickw-demo', permission_classes=[permissions.IsAdminUser])
    def test_sickw_demo(self, request):
        """
        Runs a live test against Sickw and returns a filtered response 
        (result, imei, id, status).
        """
        url = "https://sickw.com/api.php"
        api_key = getattr(settings, 'SICKW_API_KEY', None)
        
        params = {
            'format': 'json',
            'key': api_key,
            'imei': '354442067957452',
            'service': 'demo'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                raw_data = response.json()
                
                # 🔍 FILTER: Only select the specific fields you want
                filtered_response = {
                    "result": raw_data.get("result"),
                    "imei": raw_data.get("imei"),
                    "id": raw_data.get("id"),
                    "status": raw_data.get("status")
                }
                
                return Response(filtered_response, status=status.HTTP_200_OK)
            
            else:
                return Response({"error": "External API Error", "raw": response.text}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    
    serializer_class= UserServiceSerializer
    
    pagination_class = None
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()] 
        return [permissions.IsAdminUser()]   

    def get_queryset(self):
        if self.request.user.is_staff:
            return Service.objects.all() 
        return Service.objects.filter(is_active=True)
    
    def list(self, request, *args, **kwargs):
        # Ensure this function is fast/optimized, or move to Celery later
        sync_services_if_expired()
        return super().list(request, *args, **kwargs)