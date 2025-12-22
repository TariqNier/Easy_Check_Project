#authentication/models.py
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _





class UserManager(BaseUserManager):
    def create_user(self,phone_number, username, password=None, **extra_fields):
     
        if not phone_number:
            raise ValueError(_('The Phone Number field must be set'))
        if not username:
            raise ValueError(_('The Username field must be set'))

       
        user = self.model(
            phone_number=phone_number,
     
            username=username, 
            **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
            
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, username, password, **extra_fields):

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(phone_number, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    username = models.CharField(max_length=150, db_index=True)
    phone_number = PhoneNumberField(max_length=15,unique=True, db_index=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_verified = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)   
    is_staff = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    USERNAME_FIELD = 'phone_number' 
    REQUIRED_FIELDS = ['username'] 

    objects = UserManager()

    def __str__(self):
        return self.username