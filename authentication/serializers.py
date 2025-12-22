#authentication/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
import random
import string
User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(required=True, write_only=True)
    class Meta:
        model = User
        fields = ['id','phone_number', 'password','confirm_password']
        read_only_fields = ['balance', 'is_active', 'created_at','username']
        
    def create(self, validated_data):
        
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        generated_username = f"User_{random_suffix}"
        
        
        user=User.objects.create_user(
        
            username=generated_username,
            password=validated_data['password'],
            phone_number=validated_data['phone_number']
        )
        return user
    
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Password fields didn't match."})
        return data

    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # We allow the frontend to see these fields
        fields = ['id', 'username', 'phone_number', 'balance','created_at' ]
        # But we prevent them from editing them directly via API
        read_only_fields = ['id', 'username', 'phone_number', 'balance','created_at' ]