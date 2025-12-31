import datetime
import requests
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Service, Transaction
from .serializers import UserTransactionSerializer, GuestTransactionSerializer,UserServiceSerializer,AdminServiceSerializer
from .utils import get_kashier_auth_headers, place_sickw_order,sync_services_if_expired

User = get_user_model()

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    
    def get_serializer_class(self, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated:
            print("✅ Registered User Detected - Using UserTransactionSerializer")
            return UserTransactionSerializer
        
        print("⚠️ Guest User Detected - Using GuestTransactionSerializer")
        return GuestTransactionSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'kashier_webhook']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
  
        user = request.user if request.user.is_authenticated else None
        

        transaction = serializer.save(user=user)
        
        # PATH A: REGISTERED USER (Wallet Balance)
  
        if transaction.status == 'COMPLETED':
            place_sickw_order(transaction)
            
            return Response({
                "transaction_id": transaction.id,
                "transaction_status": transaction.status,
                "new_balance": user.balance, 
                "api_result": transaction.service_details.get('api_result') 
            }, status=status.HTTP_201_CREATED)
            
        merchant_redirect_logic = "http://localhost:8000/store/transactions/show-order/?merchant_transaction_id=" + str(transaction.merchant_transaction_id) if user is None else "http://localhost:8000/store/transactions/"
        # PATH B: GUEST / TOPUP (Standard Kashier Payment)
        payload = {
            "expireAt": str((datetime.datetime.now() + datetime.timedelta(minutes=30)).isoformat() + "Z"),
            "maxFailureAttempts": 3,
            "amount": str(transaction.amount) ,
            "currency": "EGP",
            "merchantId": settings.KASHIER_MID,
            "order": str(transaction.merchant_transaction_id),
            "merchantRedirect": merchant_redirect_logic, 
            "display": "en",
            "paymentType": "card",
            "serverWebhook": "https://corinne-nobler-jamir.ngrok-free.dev/store/transactions/webhook/kashier/", 
            "type": "external",
            "allowedMethods": "card,wallet,fawry,instapay,basata",
            "customer": {
                "name": str(user.phone_number) if user else "Guest",
                "email": "",
                "reference": str(user.id) if user else "guest"
            }
        }
        try:
            url = f"{settings.KASHIER_API_URL}/v3/payment/sessions"
            headers = get_kashier_auth_headers()
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()
            
      
            payment_url = response_data.get('sessionUrl')
               
        
            if payment_url:
                kashier_id = response_data.get('_id') or response_data.get('kashierOrderId')
                if kashier_id:
                    transaction.kashier_session_id = kashier_id
                    transaction.save()
                        
                return Response({
                            "status": "success",
                            "paymentUrl": payment_url, 
                            "transaction_id": transaction.id,
                            "merchant_transaction_id": str(transaction.merchant_transaction_id)
                        }, status=status.HTTP_201_CREATED)
                
            transaction.status = 'FAILED'
            transaction.save()
            return Response(response_data, status=response.status_code)  
            
        except requests.exceptions.RequestException:
            transaction.status = 'FAILED'
            transaction.save()
            return Response({"error":"Kashier service unreachable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
          
    @action(detail=False, methods=['post'], url_path='webhook/kashier')
    def kashier_webhook(self, request):
        """
        Handles the Callback from Kashier (STANDARD MODE).
        Logic: Payment Success -> Mark Completed -> Order Service
        """
        webhook_data = request.data.get('data', {})
        transaction_id = webhook_data.get('merchantOrderId')
        payment_status = webhook_data.get('status')
        kashier_txn_id = webhook_data.get('transactionId')
        
        if not transaction_id:
            return Response({"error": "No Order ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            transaction = Transaction.objects.get(merchant_transaction_id=transaction_id)
        except Transaction.DoesNotExist:
            return Response({"error": "Not Found"}, status=status.HTTP_404_NOT_FOUND)

        if transaction.status == 'COMPLETED':
             return Response({"status": "already_processed"}, status=status.HTTP_200_OK)
        
        if payment_status == "SUCCESS":
            # 1. IMMEDIATE COMPLETION (No Auth/Capture)
            transaction.status = 'COMPLETED'
            
            if kashier_txn_id:
                transaction.kashier_transaction_id = kashier_txn_id 
            if 'orderId' in webhook_data:
                transaction.kashier_session_id = webhook_data['orderId']
            
            transaction.save()
            
            # 2. Add to User Balance (If Topup)
            if transaction.is_balance_topup and transaction.user:
                transaction.user.balance += transaction.amount
                transaction.user.save()
                print(f"Topup Successful for User {transaction.user.id}")

            # 3. Order Service (If Purchase)
            elif transaction.service_details:
                place_sickw_order(transaction)
                print(f"Service Ordered for #{transaction.id}")
                
            transaction.save()
            
        else:
            transaction.status = 'FAILED'
            transaction.save()
            print(f"Payment Failed for: {transaction_id}")

        return Response({"status": "received"}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='show-order')
    def show_order(self,request):
        merchant_tx_id = request.query_params.get('merchant_transaction_id')
        if not merchant_tx_id:
            return Response({"error": "merchant_transaction_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            transaction = Transaction.objects.get(merchant_transaction_id=merchant_tx_id)
        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = GuestTransactionSerializer(transaction)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()

    
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()] 
        return [permissions.IsAdminUser()]   

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return AdminServiceSerializer
        return UserServiceSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Service.objects.all() 
        return Service.objects.filter(is_active=True)
    
    
    def list(self, request, *args, **kwargs):
        sync_services_if_expired()
    
        return super().list(request, *args, **kwargs)