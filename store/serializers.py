import re
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Service, Transaction
from .utils import is_valid_luhn

User = get_user_model()

class ServiceDetailsValidationMixin:
    def validate_service_details(self, value):
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

class TransactionSerializer(serializers.ModelSerializer, ServiceDetailsValidationMixin):
    class Meta:
        model = Transaction
        fields = ['merchant_transaction_id', 'status']
        read_only_fields = ['merchant_transaction_id', 'status']

    def validate_amount(self, data):
        if data <= 0:
            raise serializers.ValidationError("The payment amount must be greater than zero.")
        return data

class UserTransactionSerializer(TransactionSerializer):
    class Meta(TransactionSerializer.Meta):
        fields = TransactionSerializer.Meta.fields + ['service_details', 'amount']
        extra_kwargs = {
            'amount': {'required': False},
        }
    
    def validate(self, attrs):
        user = self.context['request'].user
        service_details = attrs.get('service_details')
        
        if service_details:
            service_id = service_details.get('service_id')
            
            # Try to get from cache first to avoid DB query
            cache_key = f'service_{service_id}'
            service = cache.get(cache_key)
            
            if not service:
                try:
                    service = Service.objects.get(service_id=str(service_id))
                    # Cache the service object for 1 hour
                    cache.set(cache_key, service, timeout=3600)
                except Service.DoesNotExist:
                    raise serializers.ValidationError({
                        "service_details": f"Service ID '{service_id}' does not exist in our system."
                    })
 
            if user.balance < service.final_price:
                raise serializers.ValidationError({
                    "amount": f"Insufficient balance. Cost: {service.final_price} EGP. Balance: {user.balance} EGP."
                })
            
            attrs['service_instance'] = service
        else:
            amount = attrs.get('amount')
            if not amount or amount <= 0:
                 raise serializers.ValidationError({"amount": "Amount is required for balance top-up."})
            if amount < 10:
                raise serializers.ValidationError({"amount": "Top-up amount must be atleast 10 EGP."})
            
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        service_instance = validated_data.pop('service_instance', None)
        
        with transaction.atomic():
            if service_instance:
                user_locked = User.objects.select_for_update().get(pk=user.pk)
                amount = service_instance.final_price
        
                if user_locked.balance < amount:
                     raise serializers.ValidationError("Insufficient balance.")
   
                user_locked.balance -= amount
                user_locked.save()
            
                validated_data['amount'] = amount
                validated_data['is_balance_topup'] = False
                validated_data['status'] = 'COMPLETED' 
            else:
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

        # Try to get from cache first to avoid DB query
        cache_key = f'service_{service_id}'
        service = cache.get(cache_key)
        
        if not service:
            try:
                service = Service.objects.get(service_id=service_id)
                # Cache the service object for 1 hour
                cache.set(cache_key, service, timeout=3600)
            except Service.DoesNotExist:
                raise serializers.ValidationError({
                        "service_details": f"Service ID '{service_id}' does not exist in our system."
                    })
 
        attrs['amount'] = service.final_price
        return attrs

    def create(self, validated_data):
        return Transaction.objects.create(**validated_data)

class UserServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['name', 'service_id', 'final_price', 'description']
        
class AdminServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'
        
class WalletHistorySerializer(serializers.ModelSerializer):
    transaction_type = serializers.SerializerMethodField()
    formatted_amount = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 
            'created_at', 
            'status', 
            'amount', 
            'transaction_type', 
            'formatted_amount'
        ]

    def get_transaction_type(self, obj):
        return "Top-up" if obj.is_balance_topup else "Purchase"

    def get_formatted_amount(self, obj):
 
        sign = "+" if obj.is_balance_topup else "-"
        return f"{sign}{obj.amount}"

class ServiceHistorySerializer(serializers.ModelSerializer):

    service_name = serializers.SerializerMethodField()
    item_identifier = serializers.SerializerMethodField() # IMEI or Serial
    result_text = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 
            'created_at', 
            'status', 
            'service_name', 
            'item_identifier', 
            'result_text',
            'sickw_order_id'
        ]

    def get_service_name(self, obj):
        details = obj.service_details or {}

        return details.get('service_name') or f"Service #{details.get('service_id')}"

    def get_item_identifier(self, obj):
        details = obj.service_details or {}
        return details.get('imei') or details.get('serial') or "N/A"

    def get_result_text(self, obj):
    
        details = obj.service_details or {}
        api_result = details.get('api_result')
        
        if not api_result:
            return None
            
        if isinstance(api_result, list):
            return ", ".join(map(str, api_result))

        if isinstance(api_result, str):
            return api_result
            
        if isinstance(api_result, dict):
            return api_result.get('result') or api_result.get('status')
    
        return str(api_result)