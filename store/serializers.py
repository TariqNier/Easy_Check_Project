import re
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Service, Transaction, BalanceTransaction
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
                
            if len(serial_str) < 11: 
                raise serializers.ValidationError(
                    "This service requires a legacy Serial Number (11-12 characters). 10-character (Randomized) serials are not supported."
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
                
                # Create transaction first to get the ID
                txn = super().create(validated_data)
                
                # Record balance transaction
                BalanceTransaction.objects.create(
                    user=user_locked,
                    amount=amount,
                    kind='PURCHASE',
                    source_transaction=txn,
                    note=f"Service: {service_instance.name}"
                )
                
                return txn 
            else:
                validated_data['is_balance_topup'] = True
                validated_data['status'] = 'PENDING'
                return super().create(validated_data)

class GuestTransactionSerializer(TransactionSerializer):
    service_details = serializers.JSONField(required=True) 
    guest_email = serializers.EmailField(required=True)
    
    class Meta(TransactionSerializer.Meta):
        fields = TransactionSerializer.Meta.fields + ['service_details','amount',  'created_at', 'is_balance_topup', 'service_details', 'id','guest_email']
    
    def validate(self, attrs):
        details = attrs.get('service_details')
        service_id = details.get('service_id')

        try:
            service = Service.objects.get(service_id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError({
                    "service_details": f"Service ID '{service_id}' does not exist in our system."
                })
 
        attrs['amount'] = service.final_price
        return attrs

    def create(self, validated_data):
        return Transaction.objects.create(**validated_data)

class UserServiceSerializer(serializers.ModelSerializer):
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True,coerce_to_string=False)
    
    class Meta:
        model = Service
        fields = ['id', 'service_id', 'name', 'final_price', 'description', 'is_active']
        
class BalanceTransactionSerializer(serializers.ModelSerializer):
    formatted_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = BalanceTransaction
        fields = ['id', 'created_at', 'kind', 'amount', 'formatted_amount', 'note']
    
    def get_formatted_amount(self, obj):
        if obj.kind == 'TOPUP':
            return f"+{obj.amount}"
        elif obj.kind == 'PURCHASE':
            return f"-{obj.amount}"
        elif obj.kind == 'REFUND':
            return f"+{obj.amount}"
        return str(obj.amount)
    

# 2. History Serializer for User Profile (Your Code)
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
            'merchant_transaction_id'
        ]

    def get_service_name(self, obj):
        details = obj.service_details or {}
        # Returns the name saved at the time of order, or ID if missing
        return details.get('service_name') or f"Service #{details.get('service_id')}"

    def get_item_identifier(self, obj):
        details = obj.service_details or {}
        # Smartly finds IMEI, Serial, or returns N/A
        return details.get('imei') or details.get('serial') or "N/A"

    def get_result_text(self, obj):
        return f"http://158.220.126.228:3000/result/{obj.merchant_transaction_id}"