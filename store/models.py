#store/models.py
from urllib import response
from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from decimal import Decimal as decimal
import requests
from django.conf import settings
from django.core.cache import cache

User=get_user_model()

class Transaction(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'), 
        ('REFUNDED','Refunded')
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_index=True) 
    merchant_transaction_id = models.UUIDField(max_length=100, default=uuid.uuid4, editable=False, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    
    is_balance_topup = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    service_details = models.JSONField(null=True, blank=True)
    
    sickw_order_id = models.CharField(max_length=100, blank=True, null=True)
    
    #needed for authorize/capture/void flow with Kashier
    kashier_session_id = models.CharField(max_length=255, blank=True, null=True)
    
    # This stores the "TX-xxxx" ID from Kashier. REQUIRED for Voiding.
    kashier_transaction_id = models.CharField(max_length=255, blank=True, null=True) 
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'is_balance_topup', 'created_at']),
        ]
    
    def __str__(self):
        user_identifier = self.user.phone_number if self.user else "Guest"
        return f"Order #{self.id} | {user_identifier} | {self.amount} EGP | {self.status}"






class Service(models.Model):
    name = models.CharField(max_length=255) 
    service_id = models.CharField(max_length=50, unique=True)  
    provider_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_increase_percentage = models.DecimalField( max_digits=5,  decimal_places=2, default=10.00)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True, null=True)

    @property
    def dollar_rate(self):
        cached_rate = cache.get('usd_egp_rate')
        
        if cached_rate:
            return decimal(str(cached_rate))
            
        conversion_api = settings.CONVERSION_API_KEY
        url = f'https://v6.exchangerate-api.com/v6/{conversion_api}/latest/USD'
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            rate = data['conversion_rates']['EGP']
            # Cache for 24 hours
            cache.set('usd_egp_rate', rate, timeout=86400) 
            
            return decimal(str(rate))
        except (requests.RequestException, KeyError, ValueError) as e:
            # Return a fallback rate if API fails
            # Using a reasonable default rate to prevent service disruption
            return decimal('50.00')


    @property
    def final_price(self):
        # Avoid redundant decimal conversions - convert once
        provider_price_decimal = decimal(str(self.provider_price))
        increase_decimal = decimal(str(self.price_increase_percentage)) / 100
        
        final_price = provider_price_decimal * (1 + increase_decimal)
        final_price *= self.dollar_rate
    
        return round(final_price, 2)

    def __str__(self):
        return f"{self.name} ({self.final_price} EGP)"








