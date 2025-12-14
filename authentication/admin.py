from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()

class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    model = User
    
    # The fields to be used in displaying the User model.
    list_display = ('username', 'phone_number', 'balance', 'is_staff')
    list_filter = ('is_staff', 'is_active')
    
    # Fieldsets controls the layout of the "Change User" page
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('phone_number', 'balance')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    
    # add_fieldsets controls the "Add User" page
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'phone_number', 'password'),
        }),
    )
    
    # Because we don't have first_name/last_name, we must specify ordering
    ordering = ('phone_number',)
    search_fields = ('phone_number', 'username')

admin.site.register(User, UserAdmin)