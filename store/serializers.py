#store/serializers.py
from rest_framework import serializers
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Service, Transaction

from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()



class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        
        fields = [
            'amount', 
            'merchant_transaction_id', 
            'status'
        ]
        
        read_only_fields = ['merchant_transaction_id', 'status']

    def validate_amount(self, data):
        if data <= 0:
            raise serializers.ValidationError("The payment amount must be greater than zero.")
        return data


    
# store/serializers.py

class UserTransactionSerializer(TransactionSerializer):

    class Meta(TransactionSerializer.Meta):
        fields = TransactionSerializer.Meta.fields + ['service_details']

    def create(self, validated_data):
        if not validated_data.get('service_details'):
            validated_data['is_balance_topup'] = True

            
        return super().create(validated_data)

class GuestTransactionSerializer(TransactionSerializer):
    service_details = serializers.JSONField(required=True) 
    
    class Meta(TransactionSerializer.Meta):
        fields = TransactionSerializer.Meta.fields + ['service_details']
    
    def create(self, validated_data):
        validated_data['is_balance_topup'] = False
        return super().create(validated_data)
    
    def validate(self, data):
        if not data.get("service_details"):
            raise serializers.ValidationError("Service details (IMEI/Service ID) are required for guest purchases.")
        
        return data










class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'service_id', 'price', 'description', 'is_active']

