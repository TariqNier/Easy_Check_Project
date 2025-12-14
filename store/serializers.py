#store/serializers.py
from rest_framework import serializers
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Service, Transaction
from .utils import check_imei_on_sickw
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()



class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'service_id', 'price', 'description', 'is_active']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'transaction_type', 'status', 'description', 'created_at']

class PurchaseSerializer(serializers.Serializer):
    # Input fields
    imei = serializers.CharField(min_length=8, max_length=20)
    service_id = serializers.CharField()

    def validate(self, data):
        """
        Level 1 Check: Does the service exist?
        """
        service_id = data.get('service_id')
        service = get_object_or_404(Service, service_id=service_id, is_active=True)
        
        # We store the service object in context so we can use it later in create()
        self.context['service'] = service
        return data

    def create(self, validated_data):
        """
        Level 2: The Business Logic
        This runs when view calls serializer.save()
        """
        user = self.context['request'].user
        service = self.context['service']
        imei = validated_data['imei']

    
        try:
            with transaction.atomic():
                # 1. Lock & Check Balance
                user = type(user).objects.select_for_update().get(id=user.id)
                
                if user.balance < service.price:
                    raise serializers.ValidationError("Insufficient balance.")

                # 2. Deduct Money
                user.balance -= service.price
                user.save()

                # 3. Call External API
                api_result = check_imei_on_sickw(imei, service_id=service.service_id)
                if not api_result['success']:
                    raise serializers.ValidationError(api_result['error'])

                # 4. Create Receipt
                transaction_record = Transaction.objects.create(
                    user=user,
                    amount=service.price,
                    transaction_type='PURCHASE',
                    status='COMPLETED',
                    description=f"{service.name} - IMEI: {imei}"
                )
                
                # Attach the actual API result to the object so the View can read it
                transaction_record.api_result = api_result['result']
                
                return transaction_record

        except Exception as e:
            # Re-raise the error so the View handles it correctly
            raise serializers.ValidationError(str(e))
        
        
# store/serializers.py

class DepositSerializer(serializers.Serializer):
    # Define the fields we expect from Kashier
    paymentStatus = serializers.CharField()
    merchantOrderId = serializers.CharField()
    transactionId = serializers.CharField()
    amount = serializers.FloatField()

    def validate(self, data):
        """
        Level 1: Validation
        Check if payment was actually successful and not a duplicate.
        """
        # 1. Check Status
        if data['paymentStatus'] != 'SUCCESS':
            raise serializers.ValidationError("Payment Failed")

        # 2. Check for Duplicate (Replay Attack)
        # If we already recorded this transaction ID, stop.
        if Transaction.objects.filter(description__contains=data['transactionId']).exists():
            raise serializers.ValidationError("Transaction already processed")

        # 3. Find the User
        merchant_order_id = data['merchantOrderId']
        try:
            user_id = merchant_order_id.split('-')[0] # "5-12345" -> "5"
            user = User.objects.get(id=user_id)
            # Store user in context to use it later
            self.context['target_user'] = user
        except (IndexError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid Merchant Order ID")

        return data

    def create(self, validated_data):
        """
        Level 2: Execution
        Update the wallet atomically.
        """
        user = self.context['target_user']
        amount = Decimal(validated_data['amount'])
        txn_ref = validated_data['transactionId']

        # Atomic Balance Update
        with transaction.atomic():
            # Lock the user row again for safety
            user = type(user).objects.select_for_update().get(id=user.id)
            
            user.balance += amount
            user.save()

            transaction_record = Transaction.objects.create(
                user=user,
                amount=amount,
                transaction_type='DEPOSIT',
                status='COMPLETED',
                description=f"Kashier Deposit - Ref: {txn_ref}"
            )
        
        return transaction_record
