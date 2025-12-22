#authentication/views.py
from rest_framework import viewsets,permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer, UserSerializer
ModelViewSet = viewsets.ModelViewSet
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

User = get_user_model()

  
class CustomAuthToken(ObtainAuthToken):
    #phone number will be named username
    # 'username : 0123456789',
    # 'password : yourpassword'
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'username': user.username, 
            'user_id': user.pk,
            'phone_number': str(user.phone_number),
            'balance': user.balance,
            'created_at': user.created_at
                    
        })   
   



# Create your views here.

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    search_fields = ['username', 'phone_number'] 
    filterset_fields = ['is_active', 'is_staff']
    
    def get_serializer_class(self):
        if self.action == 'register':
            return UserRegistrationSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action in ['register','login']:
            return [permissions.AllowAny()]
        elif self.action in ['user_info','logout']:
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.IsAdminUser()]

    @action(detail=False,methods=['post'],url_name='register', url_path='register')
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            "status": "success",
            "message": "User created successfully",
        }, status=status.HTTP_201_CREATED)
    
    
    def create(self, request, *args, **kwargs):
        return self.register(request)        
        
        #Custom Action: "My profile"
        # URL : /api/users/me/
    @action(detail=False,methods =['get'], url_name='user_info', url_path='user_info')
    def user_info(self,request):
        serializer= self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_name='logout', url_path='logout')
    def logout(self, request):
        request.auth.delete() 
        return Response({"status": "success", "message": "Logged out successfully."}, status=status.HTTP_200_OK)

   
    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     user = serializer.save()
        
    #     return Response({
    #         "status": "success",
    #         "message": "User created successfully",
    #         "user_id": user.id,
    #         "phone": user.phone_number,
    #         "username": user.username
    #     }, status=status.HTTP_201_CREATED)
        
        