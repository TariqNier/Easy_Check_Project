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

admin.site.register(Transaction)