#store/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Service, Transaction
from .serializers import TransactionSerializer, UserTransactionSerializer, GuestTransactionSerializer
from rest_framework.decorators import action
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
import urllib.parse
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Transaction
from .serializers import TransactionSerializer
from .utils import get_kashier_auth_headers
# store/views.py
import requests
import datetime




User = get_user_model()

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    
    def get_serializer_class(self, *args, **kwargs):
        user=self.request.user

        if user.is_authenticated:
            return UserTransactionSerializer
        return GuestTransactionSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def create(self, request, *args, **kwargs):
        
        serializer= self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user=request.user if request.user.is_authenticated else None
        transaction = serializer.save(user=user)
        
        
        payload = {
            "expireAt": str((datetime.datetime.now() + datetime.timedelta(minutes=30)).isoformat() + "Z"),
            "maxFailureAttempts": 3,
            "amount": str(transaction.amount),
            "currency": "EGP",
            "merchantId": settings.KASHIER_MID,
            #"mode":"test",
            "order": str(transaction.merchant_transaction_id),
            "merchantRedirect": "https://www.google.com",
            "display": "en",
            "paymentType": "credit",
            "type":"external",
            "allowedMethods": "card,wallet,fawry,instapay,basata",
            "customer": {
                "name": user.phone_number if user else "Guest",
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
                        "transaction_id": transaction.id
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
    
    
    