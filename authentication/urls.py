#authentication/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet
from rest_framework.authtoken.views import obtain_auth_token

app_name = 'authentication'  

# Create a router and register our ViewSet
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
  
    # This includes the router URLs (e.g., /api/auth/users/)
    path('', include(router.urls)),
    path('login/', obtain_auth_token, name='api_token_auth'),
]