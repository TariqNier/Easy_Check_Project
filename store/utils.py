# store/utils.py
from django.conf import settings
import hmac
import hashlib

def get_kashier_auth_headers():
    return {
        "Authorization": settings.KASHIER_SECRET_KEY,
        "api-key": settings.KASHIER_API_KEY,       
        "Content-Type": "application/json"
    }


def verify_kashier_signature(data, incoming_signature):
    secret_key = settings.KASHIER_API_KEY
    
    sorted_keys = sorted(data.keys())
    
    params= []
    for key in sorted_keys:
        if key not in ['signature', 'hash','mode']:
            params.append(f"{key}={data[key]}")
    
    query_string = "&".join(params)
            
    path="/"
    final_string = path + query_string.lstrip("&")
    
    signature = hmac.new(
        key=secret_key.encode('utf-8'),
        msg=final_string.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, incoming_signature)
    
    
   