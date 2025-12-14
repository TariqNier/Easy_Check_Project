#authentication/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .forms import CustomUserCreationForm, CustomUserChangeForm

User = get_user_model()

class UserAdmin(BaseUserAdmin):
    # Connect the forms
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    
    # Columns to show in the list
    list_display = ('phone_number', 'username', 'balance', 'is_staff')
    list_filter = ('is_staff', 'is_active')
    
    # Layout for ADDING a user (Must match CustomUserCreationForm fields + passwords)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'username', 'password1', 'password2'),
        }),
    )
    
    # Layout for EDITING a user
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal info', {'fields': ('username', 'balance')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    
    ordering = ('phone_number',)
    search_fields = ('phone_number', 'username')

admin.site.register(User, UserAdmin)