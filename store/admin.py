# store/admin.py
from django.contrib import admin
from .models import Service, Transaction, BalanceTransaction

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    # Show these columns in the list
    list_display = ('name', 'service_id', 'provider_price', 'price_increase_percentage', 'final_price', 'is_active')
    
    # Allow searching by name or ID
    search_fields = ('name', 'service_id')
    
    list_per_page = 15
    
    # Allow editing the % and Active status directly from the list view (super convenient!)
    list_editable = ('price_increase_percentage', 'is_active') 
    
    list_filter = ('is_active',)

# Your Transaction Admin (keep as is or update if needed)
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'status', 'created_at','merchant_transaction_id')
    list_filter = ('status', 'created_at')
    
    
@admin.register(BalanceTransaction)
class BalanceTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'kind', 'created_at')
    list_filter = ('kind', 'created_at')