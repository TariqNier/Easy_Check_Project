import re
from django.core.exceptions import ValidationError


class CustomPasswordValidator:
    def validate(self,password,user=None):
        if not re.search(r'[A-Z]',password):
            raise ValidationError(
                "Password must contain at least one uppercase letter,",
                code='password_no_upper',
            )
            
        if not re.search(r'[a-z]',password):
            raise ValidationError(
                "Password must contain at least one lowercase letter,",
                code='password_no_lower',
            )
        
        if not re.search(r'[0-9]',password):
            raise ValidationError(
                "Password must contain at least one digit,",
                code='password_no_digit',
            )
            
            
    def get_help_text(self):
        return "Your password must be atleast 8 characters long and contain at least one uppercase letter, one lowercase letter, and one digit."
        

