#authentication/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet
from .views import CustomAuthToken

app_name = 'authentication'  

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [

    path('', include(router.urls)), 
    path('login/', CustomAuthToken.as_view(), name='login'),
]


#localhost:8000/users/register/
#localhost:8000/login/