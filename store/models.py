#store/models.py
from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User=get_user_model()


class Transaction(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
     )

    
    user = models.ForeignKey(User, on_delete=models.SET_NULL,null=True, blank=True) 
    merchant_transaction_id = models.UUIDField(max_length=100, default=uuid.uuid4, editable=False, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    is_balance_topup = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    service_details = models.JSONField(null=True, blank=True)











class Service(models.Model):
    name = models.CharField(max_length=100) 
    service_id = models.CharField(max_length=50, unique=True)  
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} (${self.price})"








