# store/serializers.py
import requests
from decimal import Decimal
from django.conf import settings
from rest_framework import serializers
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .utils import is_valid_luhn

from .models import Service, Transaction
User = get_user_model()

import re # Import Regex for serial validation

class ServiceDetailsValidationMixin:
    def validate_service_details(self, value):
        # 1. Ensure value is a dictionary
        if not isinstance(value, dict):
            return value

        imei = value.get('imei')
        serial = value.get('serial') 

   
        if imei:
            imei_str = str(imei)
            
            if not imei_str.isdigit() or len(imei_str) != 15:
                raise serializers.ValidationError(
                    "IMEI must be exactly 15 digits and contain only numbers."
                )

            if not is_valid_luhn(imei_str):
                raise serializers.ValidationError(
                    "Invalid IMEI number (Checksum failed). Please check for typos."
                )

        elif serial:
            serial_str = str(serial).strip().upper()
            
           
            if len(serial_str) < 4 or len(serial_str) > 20:
                raise serializers.ValidationError(
                    "Serial Number seems too short or too long."
                )

         
            if not re.match(r'^[A-Z0-9]+$', serial_str):
                raise serializers.ValidationError(
                    "Serial Number must contain only letters and numbers (No spaces or dashes)."
                )
      
        return value

class TransactionSerializer(serializers.ModelSerializer,ServiceDetailsValidationMixin):
    class Meta:
        model = Transaction
        
        fields = [
            'merchant_transaction_id', 
            'status',
        ]
        
        read_only_fields = ['merchant_transaction_id', 'status']

    def validate_amount(self, data):
        if data <= 0:
            raise serializers.ValidationError("The payment amount must be greater than zero.")
        return data


    
# store/serializers.py

class UserTransactionSerializer(TransactionSerializer):


    class Meta(TransactionSerializer.Meta):
        fields = TransactionSerializer.Meta.fields + ['service_details', 'amount']
        
 
        extra_kwargs = {
            'amount': {'required': False},
            
        }
    
    
    def validate(self, attrs):
        user = self.context['request'].user
        service_details = attrs.get('service_details')
        
        # --- SCENARIO A: Buying a Service (Strict Mode) ---
        if service_details:
            service_id = service_details.get('service_id')
            try:
                service = Service.objects.get(service_id=str(service_id))
            except Service.DoesNotExist:
                raise serializers.ValidationError({
                    "service_details": f"Service ID '{service_id}' does not exist in our system."
                })
 
            if user.balance < service.final_price:
                raise serializers.ValidationError({
                    "amount": f"Insufficient balance. Cost: {service.final_price} EGP. Balance: {user.balance} EGP."
                })
        else:
            amount = attrs.get('amount')
            if not amount or amount <=0:
                 raise serializers.ValidationError({"amount": "Amount is required for balance top-up."})
            if amount < 10:
                raise serializers.ValidationError({"amount": "Top-up amount must be atleast 10 EGP."})
            
        return attrs
    
    


    def create(self, validated_data):
        user = self.context['request'].user
        
        service_details=validated_data.get('service_details')
        if service_details:
            service=Service.objects.get(service_id=service_details['service_id'])
            amount = service.final_price
   
            user.balance -= amount
            user.save()
            
    
            validated_data['amount'] = amount
            validated_data['is_balance_topup'] = False
            validated_data['status'] = 'COMPLETED' 
            
        else:
            # --- TOPUP (Kashier) ---
            validated_data['is_balance_topup'] = True
            validated_data['status'] = 'PENDING'  

        return super().create(validated_data)

class GuestTransactionSerializer(TransactionSerializer):
    service_details = serializers.JSONField(required=True) 
    
    class Meta(TransactionSerializer.Meta):
        fields = TransactionSerializer.Meta.fields + ['service_details']
    
    def validate(self, attrs):
        details = attrs.get('service_details')

        service_id = details.get('service_id')

        try:
            service = Service.objects.get(service_id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError({
                    "service_details": f"Service ID '{service_id}' does not exist in our system."
                })
 

        real_price = service.final_price
        
        attrs['amount'] = real_price
        
        return attrs

    def create(self, validated_data):
   
        return Transaction.objects.create(**validated_data)










class UserServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [ 'name', 'service_id', 'final_price', 'description']
        
class AdminServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'

    
    # def validate(self, attrs):
    #     user = self.context['request'].user
    #     service_details = attrs.get('service_details')
        
    #     if service_details:
    #         service_id = service_details.get('service_id')
            
    #         try:
    #             api_key = getattr(settings, 'SICKW_API_KEY', None)
    #             if not api_key:
    #                 raise serializers.ValidationError({"error": "Server configuration error (Missing API Key)."})

    #             response = requests.post("https://sickw.com/api.php", data={'key': api_key, 'action': 'services'})
    #             data = response.json()
    #             service_list = data.get("Service List", [])
                
    #             sickw_item = next((item for item in service_list if item['service'] == str(service_id)), None)
                
    #             if not sickw_item:
    #                 raise serializers.ValidationError({"service_details": "This service is currently unavailable on Sickw."})
                
    #             live_cost = Decimal(sickw_item['price'])
                
    #             try:
    #                 local_service = Service.objects.get(service_id=str(service_id))
    #                 percentage = local_service.price_increase_percentage
    #             except Service.DoesNotExist:
    #                 percentage = Decimal(10.00)
                
    #             increase = (live_cost * percentage) / 100
    #             final_amount = round(live_cost + increase, 2)
                
    #             attrs['amount'] = final_amount
                
    #         except requests.exceptions.RequestException as e:
    #             print(f"❌ SICKW CONNECTION ERROR: {e}") 
    #             raise serializers.ValidationError({"error": f"Unable to verify price: {str(e)}"})

    #         if user.balance < final_amount:
    #             raise serializers.ValidationError({
    #                 "amount": f"Insufficient balance. The live price is {final_amount} EGP, but you have {user.balance} EGP."
    #             })
                
    #     else:
    #         if not attrs.get('amount'):
    #              raise serializers.ValidationError({"amount": "Amount is required for balance top-up."})
        
    #     return attrs
