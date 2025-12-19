#system/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Auth Routes
    path('', include('authentication.urls')),
    path('api/store/', include('store.urls')),
]