#store/models.py
from django.db import models
from django.conf import settings 
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User=get_user_model()

class Service(models.Model):
    """
    Stores the services you offer (e.g., Sickw Check, Unlocking).
    Admins can update 'price' here, and it updates the app instantly.
    """
    name = models.CharField(max_length=100)  # e.g. "Sickw Info"
    service_id = models.CharField(max_length=50, unique=True)  # The ID sent to Sickw (e.g. "10")
    
    
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} (${self.price})"

class Transaction(models.Model):
    """
    The "Paper Trail". Logs every single movement of money.
    """
    TRANSACTION_TYPES = (
        ('DEPOSIT', 'Deposit'),       
        ('PURCHASE', 'Purchase'),   
        ('REFUND', 'Refund'),        
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    is_guest=models.BooleanField(default=False)
    guest_email=models.EmailField(null=True)

    user = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='transactions',
        null=True
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Extra info (e.g., "Sickw Check for IMEI 3582...")
    description = models.CharField(max_length=255) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.transaction_type} - ${self.amount}"