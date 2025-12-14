from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    def create_user(self,phone_number, email, username, password=None, **extra_fields):
        # 1. Check for empty fields
        if not phone_number:
            raise ValueError(_('The Phone Number field must be set'))
        if not username:
            raise ValueError(_('The Username field must be set'))

        # 2. Normalize email (converts SomeOne@Gmail.com to someone@gmail.com)
        email = self.normalize_email(email)
        
        user = self.model(
            phone_number=phone_number,
            email=email, 
            username=username, 
            **extra_fields
        )

        # 3. Handle Password
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
            
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, email, username, password, **extra_fields):
        # Force these settings for Admin
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(phone_number,email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    # Core Fields
    username = models.CharField(max_length=150, unique=True, db_index=True)
    email = models.EmailField(max_length=255, unique=True, db_index=True,blank=True,null=True) 
    phone_number = models.CharField(max_length=15,unique=True, db_index=True)
    
    # Project Specific Fields
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Status Fields
    is_verified = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)   
    is_staff = models.BooleanField(default=False) 
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Login Settings
    USERNAME_FIELD = 'phone_number'  # Login with Phone Number
    REQUIRED_FIELDS = ['username','email'] # Ask for username when running 'createsuperuser'

    objects = UserManager()

    def __str__(self):
        return self.username