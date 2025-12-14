#authentcation/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    # Explicitly define password fields so Admin works correctly
    password1 = forms.CharField(
        label="Password", 
        widget=forms.PasswordInput, 
        strip=False
    )
    password2 = forms.CharField(
        label="Password confirmation", 
        widget=forms.PasswordInput, 
        strip=False
    )

    class Meta:
        model = User
        # ONLY put database fields here
        fields = ('phone_number', 'username')

    def save(self, commit=True):
        # Manually handle the password hashing
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('phone_number', 'username', 'balance', 'is_active', 'is_staff', 'is_superuser')







# from django import forms
# from django.contrib.auth.forms import UserCreationForm, UserChangeForm
# from django.contrib.auth import get_user_model

# User = get_user_model()

# class CustomUserCreationForm(UserCreationForm):
#     # 1. CRASH FIX: Explicitly define password fields so Admin doesn't crash
#     password1 = forms.CharField(
#         label="Password", 
#         widget=forms.PasswordInput, 
#         strip=False
#     )
#     password2 = forms.CharField(
#         label="Password confirmation", 
#         widget=forms.PasswordInput, 
#         strip=False
#     )

#     class Meta:
#         model = User
#         # ONLY put database fields here
#         fields = ('phone_number', 'username')

#     # 2. DEBUG LOGIC: Restore the print statements you wanted
#     def clean(self):
#         cleaned_data = super().clean()
        
#         if self.errors:
#             print("\n" + "="*30)
#             print("❌ REGISTRATION ERROR FOUND:")
#             for field, error in self.errors.items():
#                 print(f"👉 Field: {field}")
#                 print(f"   Error: {error}")
#             print("="*30 + "\n")
            
#         return cleaned_data

#     # 3. SAVE LOGIC: Manually handle the password hashing
#     def save(self, commit=True):
#         user = super().save(commit=False)
#         user.set_password(self.cleaned_data["password1"])
#         if commit:
#             user.save()
#         return user

# class CustomUserChangeForm(UserChangeForm):
#     class Meta:
#         model = User
#         fields = ('phone_number', 'username', 'balance', 'is_active', 'is_staff', 'is_superuser')