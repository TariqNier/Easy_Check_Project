#authentication/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet
from rest_framework.authtoken.views import obtain_auth_token

app_name = 'authentication'  

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [

    path('', include(router.urls)), 
    path('login/', obtain_auth_token, name='api_token_auth'),
]


#localhost:8000/users/register/
#localhost:8000/users/login/