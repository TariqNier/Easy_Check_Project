# store/utils.py
import requests
import hmac
import hashlib
from django.conf import settings
from django.core.cache import cache
from .models import Service

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
    
# store/utils.py

def place_sickw_order(transaction_obj):
    print("#"*50)
    print(f"🔄 Attempting to process Sickw order for Trx #{transaction_obj.id}...")

    details = transaction_obj.service_details or {}
    service_id = details.get('service_id')
    imei = details.get('imei')
    serial = details.get('serial')
    print(f" Service ID: {service_id}, IMEI: {imei}, Serial: {serial}")
    
    if imei or serial:
        pass
    else:
        print(" Error: Missing IMEI or Serial Number.")
        return False
    
    
    if not service_id:
        print(" Error: Missing Service ID.")
        return False

    api_key = getattr(settings, 'SICKW_API_KEY', None)
    url = "https://sickw.com/api.php"


    params = {
        'key': api_key,
        'action': 'order',
        'service': 'demo',
        'imei': 354442067957452,
        'format': 'json'
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response_text = response.text
        
        data = response.json()
        transaction_obj.service_details['api_result'] = data
        transaction_obj.sickw_order_id = data.get('id')
        transaction_obj.save()

    
        error_keywords = [
            "IMEI is Wrong", "Invalid IMEI", "Not Found", "Error E01", 
            "Rejected", "Not supported", "Insufficient Funds", 
            "Service is Down", "Service ID is Wrong"
        ]

        for keyword in error_keywords:
            if keyword.lower() in response_text.lower():
                print(f" Error detected in Sickw response: {keyword}")
                return False 

        # 4. If no errors were found
        print(" Service ordered successfully")
        transaction_obj.sickw_order_id = service_id
        transaction_obj.save()
        return True  # Return True because it succeeded

    except requests.RequestException as e:
        print(f" Network/Connection Error: {e}")
        return False
    
    
def sync_services_if_expired():
    if cache.get('sickw_sync_lock'):
        print("Already synced recently ")
        return 
    api_key = getattr(settings, 'SICKW_API_KEY', None)
    url = "https://sickw.com/api.php"
    params = {'key': api_key, 'action': 'services'}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        service_list = data.get("Service List", [])

        if not service_list:
            return 

      
        for item in service_list:
            Service.objects.update_or_create(
                service_id=str(item['service']),
                defaults={
                    'name': item['name'],
                    'provider_price': item['price'],
                }
            )

        cache.set('sickw_sync_lock', True, timeout=21600) 
        print("Sync Complete. Sleeping for 6 hours.")

    except Exception as e:
        print(f"Sync Failed (Using old data): {e}")    
  
  
  

def is_valid_luhn(imei):
    if not imei.isdigit():
        return False
        
    digits = [int(d) for d in imei]
    # 1. Reverse the digits
    digits = digits[::-1]
    
    checksum = 0
    
    # 2. Loop through digits
    for i, digit in enumerate(digits):
        if i % 2 == 1: 
            doubled = digit * 2
            if doubled > 9:
                doubled -= 9
            checksum += doubled
        else:
            checksum += digit
            
    return checksum % 10 == 0