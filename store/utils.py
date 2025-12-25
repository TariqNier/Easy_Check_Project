# store/utils.py
from django.conf import settings

def get_kashier_auth_headers():
    return {
        "Authorization": settings.KASHIER_SECRET_KEY,
        "api-key": settings.KASHIER_API_KEY,       
        "Content-Type": "application/json"
    }


def verify_kashier_signature(data, incoming_signature):
 
    return True