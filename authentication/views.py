from django.shortcuts import render
from rest_framework import viewsets,permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer, UserSerializer
ModelViewSet = viewsets.ModelViewSet

User = get_user_model()


# Create your views here.

class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    
    search_fields = ['username', 'phone', 'email', 'first_name'] 
    
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
        
        #Custom Action: "My profile"
        # URL : /api/users/me/
    @action(detail=False,methods =['get'], url_name='me', url_path='me')
    def me(self,request):
        serializer= self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    