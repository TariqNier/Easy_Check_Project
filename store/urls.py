#store/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import  TransactionViewSet,ServiceViewSet

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'transactions', TransactionViewSet, basename='transaction')


urlpatterns = [
    path('', include(router.urls)),
]