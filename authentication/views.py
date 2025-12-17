#authentication/views.py
from django.shortcuts import render
from rest_framework import viewsets,permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer, UserSerializer
ModelViewSet = viewsets.ModelViewSet
from django.contrib.auth import authenticate

User = get_user_model()


# Create your views here.

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    search_fields = ['username', 'phone_number'] 
    filterset_fields = ['is_active', 'is_staff']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        elif self.action == 'list':
            return [permissions.IsAdminUser()]
        elif self.action == 'me':
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.IsAdminUser()]


    # This gives you that nice custom JSON response when someone registers.
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            "status": "success",
            "message": "User created successfully",
            "user_id": user.id,
            "phone": user.phone_number,
            "username": user.username
        }, status=status.HTTP_201_CREATED)
        
        #Custom Action: "My profile"
        # URL : /api/users/me/
    @action(detail=False,methods =['get'], url_name='me', url_path='me')
    def me(self,request):
        serializer= self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    @action(detail=False, methods=['post'], url_path='login', url_name='login')
    def login(self, request, pk=None):
        phone_number=request.data.get('phone_number')
        password=request.data.get('password')
        
        if not phone_number:
            return Response({'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        user=authenticate(username=phone_number, password=password)
        #not complete