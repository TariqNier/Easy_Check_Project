from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

app_name = 'authentication'  

# Create a router and register our ViewSet
router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
   
    path('', include(router.urls)),
]