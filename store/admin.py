#store/admin.py
from django.contrib import admin
from .models import Service, Transaction

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    # What columns to show in the list
    list_display = ('name', 'service_id', 'price', 'is_active')
    
    # Allows you to edit these directly in the list view (Fast!)
    list_editable = ('price', 'is_active')
    
    # Add a search bar to find services by name
    search_fields = ('name', 'service_id')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    # Show the most important info
    list_display = ('user', 'transaction_type', 'amount', 'status', 'created_at')
    
    # Add filters on the right side (e.g., show only FAILED deposits)
    list_filter = ('transaction_type', 'status', 'created_at')
    
    # Search by User's phone number or the transaction description
    search_fields = ('user__phone_number', 'description')
    
    # SECURITY: Make the detail view Read-Only.
    # This prevents admins from manually editing a transaction log.
    readonly_fields = ('user', 'amount', 'transaction_type', 'status', 'description', 'created_at')

    # DISABLE DELETE: Prevent accidental deletion of financial records
    def has_delete_permission(self, request, obj=None):
        return False

    # DISABLE ADD: Transactions should only be created by the System (API), not manually
    def has_add_permission(self, request):
        return False