from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'phone_number']
        read_only_fields = ['balance', 'is_active', 'created_at']
        
    def create(self, validated_data):
        user=User.objects.create_user(
            email=validated_data.get('email',None),
            username=validated_data['username'],
            password=validated_data['password'],
            phone_number=validated_data['phone_number']
        )
        return user
    
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # We allow the frontend to see these fields
        fields = ['id', 'username', 'email', 'phone_number', 'balance', 'is_verified']
        # But we prevent them from editing them directly via API
        read_only_fields = ['balance', 'is_verified', 'email', 'phone_number']