# store/views.py
import datetime
import requests
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Service, Transaction
from .serializers import UserTransactionSerializer, GuestTransactionSerializer
from .utils import get_kashier_auth_headers
User = get_user_model()

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    
    def get_serializer_class(self, *args, **kwargs):
        user=self.request.user

        if user.is_authenticated:
            return UserTransactionSerializer
        
        return GuestTransactionSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'kashier_webhook']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def create(self, request, *args, **kwargs):
        
        serializer= self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user=request.user if request.user.is_authenticated else None
        
        if user and serializer.validated_data.get('service_details'):
            amount = serializer.validated_data.get('amount')
        
            if user.balance < amount:
                return Response({"error":"Insufficient balance",'Current Balance':user.balance}, status=status.HTTP_400_BAD_REQUEST)
        
            user.balance -= amount
            user.save()
            
            transaction = serializer.save(user=user, status='COMPLETED', is_balance_topup=False)
            
            imei = transaction.service_details.get('imei')
            print(f"(User) Triggering Unlocking API for IMEI: {imei}")
            
            return Response({
                "status": "success",
                "transaction_id": transaction.id,
                "transaction_status": transaction.status,
                "new_balance": user.balance,
            }, status=status.HTTP_201_CREATED)
            
        transaction = serializer.save(user=user)
        
        
        payload = {
            "expireAt": str((datetime.datetime.now() + datetime.timedelta(minutes=30)).isoformat() + "Z"),
            "maxFailureAttempts": 3,
            "amount": str(transaction.amount),
            "currency": "EGP",
            "merchantId": settings.KASHIER_MID,
            #"mode":"test",
            "order": str(transaction.merchant_transaction_id),
            "merchantRedirect": "http://localhost:5173/",
            "display": "en",
            "paymentType": "credit",
            "serverWebhook": "https://corinne-nobler-jamir.ngrok-free.dev/store/transactions/webhook/kashier/",
            "type":"external",
            "allowedMethods": "card,wallet,fawry,instapay,basata",
            "customer": {
                "name": str(user.phone_number) if user else "Guest",
                "email": "",
                "reference": str(user.id) if user else "guest"
            }
        }
        
        try:
            url=f"{settings.KASHIER_API_URL}/v3/payment/sessions"
            headers= get_kashier_auth_headers()

            response = requests.post(url, json=payload, headers= headers)
            response_data = response.json()
            
            if response.status_code in [200, 201, 202]:
        
                payment_url = response_data.get('sessionUrl') or \
                              response_data.get('paymentUrl') or \
                              response_data.get('data', {}).get('redirectUrl')

                if payment_url:
                    kashier_id = response_data.get('_id') or response_data.get('kashierOrderId')
                    
                    if kashier_id:
                        transaction.kashier_session_id = kashier_id
                        transaction.save()
                    
                    # 3. RETURN TO FRONTEND
                    return Response({
                        "status": "success",
                        "paymentUrl": payment_url, 
                        "transaction_id": transaction.id,
                        "merchant_transaction_id": str(transaction.merchant_transaction_id)
                    }, status=status.HTTP_201_CREATED)
            
            print("Kashier Error Response:", response_data)
            transaction.status = 'FAILED'
            transaction.save()
            return Response(response_data, status=response.status_code)  
        
        except requests.exceptions.RequestException as e:
            print("Kashier Exception:", str(e))
            transaction.status = 'FAILED'
            transaction.save()
            return Response({"error":"Kashier service unreachable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
          
    @action(detail=False, methods=['post'], url_path='webhook/kashier')
    def kashier_webhook(self, request):
  
        
        webhook_data = request.data.get('data', {})
        transaction_id = webhook_data.get('merchantOrderId')
        payment_status = webhook_data.get('status')
        
                    
        if not transaction_id:
            return Response({"error": "No Order ID"}, status=status.HTTP_400_BAD_REQUEST)

        
        try:
            transaction = Transaction.objects.get(merchant_transaction_id=transaction_id)
        except Transaction.DoesNotExist:
            return Response({"error": "Not Found"}, status=status.HTTP_404_NOT_FOUND)

       
        if transaction.status == 'COMPLETED':
            return Response({"status": "already_processed"}, status=status.HTTP_200_OK)

        if payment_status == "SUCCESS":
            transaction.status = 'COMPLETED'
            
            
            if 'orderId' in webhook_data:
                transaction.kashier_session_id = webhook_data['orderId']
            
            transaction.save()
            print(f"Payment Verified: {transaction_id}")

            if transaction.is_balance_topup and transaction.user:
                transaction.user.balance += transaction.amount
                transaction.user.save()
                print(f"User {transaction.user.id} balance topped up by {transaction.amount}. New balance: {transaction.user.balance}")
            elif transaction.service_details:
                imei = transaction.service_details.get('imei')
                print(f"(Guest) Triggering Unlocking API for IMEI: {imei}")
                
        
        else:
            transaction.status = 'FAILED'
            transaction.save()
            print(f"Payment Failed for: {transaction_id}")

        return Response({"status": "received"}, status=status.HTTP_200_OK)        

















    
    # def create(self,request, *args, **kwargs):
    #     serializer= self.get_serializer(data=request.data, context={'request': request})
    #     serializer.is_valid(raise_exception=True)
        
    #     if request.user.is_authenticated:
    #         user=request.user
    #     else:
    #         user=None
        
    #     transaction = serializer.save(user=user)
        
    #     payload = {
    #         "amount": str(transaction.amount),
    #         "currency": "EGP",
    #         "merchant_transaction_id": str(transaction.merchant_transaction_id),
    #         "operation": "purchase",
    #         "customerName": user.username if user else "Guest",
    #     }
        
    #     try:
    #         url = f"{settings.KASHIER_API_URL}/payment/session"
    #         headers = get_kashier_auth_headers()
    #         response = requests.post(url, json=payload, headers=headers)
    #         response_data = response.json()
            
    #         if response.status_code in [200,201]:
    #             return Response({
    #                 "sessionToken": response_data.get("sessionToken"),
    #                 "merchantTransactionId": str(transaction.merchant_transaction_id),
    #                 "id": transaction.id
    #             }, status=status.HTTP_201_CREATED)
            
    #         return Response(response_data, status=response.status_code)
    
    #     except requests.exceptions.RequestException as e:
    #         return Response({"error":"Kashier service unreachable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    
    