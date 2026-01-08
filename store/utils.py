import requests
import hmac
import hashlib
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from .models import Service

def get_kashier_auth_headers():
    return {
        "Authorization": settings.KASHIER_SECRET_KEY,
        "api-key": settings.KASHIER_API_KEY,       
        "Content-Type": "application/json"
    }

def verify_kashier_signature(data, incoming_signature):
    secret_key = settings.KASHIER_API_KEY
    # Sort keys alphabetically to match Kashier's signing logic
    sorted_keys = sorted(data.keys())
    params = []
    for key in sorted_keys:
        if key not in ['signature', 'hash', 'mode']:
            params.append(f"{key}={data[key]}")
    
    query_string = "&".join(params)
    # Note: verify if Kashier needs the leading '/' or not based on their latest doc
    # Usually it's path + "?" + query. If path is just "/", then:
    path = "/"
    final_string = path + query_string.lstrip("&")
    
    signature = hmac.new(
        key=secret_key.encode('utf-8'),
        msg=final_string.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, incoming_signature)

def place_sickw_order(transaction_obj):
    """
    Places an order on Sickw.
    If it fails (e.g. Invalid IMEI), it AUTO-REFUNDS the user.
    """
    print("#"*50)
    print(f"🔄 Attempting to process Sickw order for Trx #{transaction_obj.id}...")

    details = transaction_obj.service_details or {}
    service_id = details.get('service_id')
    imei = details.get('imei')
    serial = details.get('serial')
    
    if not service_id:
        print("❌ Error: Missing Service ID.")
        return False

    api_key = getattr(settings, 'SICKW_API_KEY', None)
    url = "https://sickw.com/api.php"

    params = {
        'key': api_key,
        'action': 'order',
        'service': service_id,
        'format': 'json'
    }
    if imei:
        params['imei'] = imei
    if serial:
        params['serial'] = serial

    try:
        response = requests.get(url, params=params, timeout=30)
        response_text = response.text
        
        # Try parsing JSON, but Sickw sometimes returns raw text on error
        try:
            data = response.json()
            # Save the Sickw Order ID immediately
            if 'id' in data:
                transaction_obj.sickw_order_id = data.get('id')
            transaction_obj.service_details['api_result'] = data
        except ValueError:
            transaction_obj.service_details['api_result'] = {"raw": response_text}

        transaction_obj.save()

        # Check for known errors
        error_keywords = [
            "IMEI is Wrong", "Invalid IMEI", "Not Found", "Error E01", 
            "Rejected", "Not supported", "Insufficient Funds", 
            "Service is Down", "Service ID is Wrong"
        ]

        is_error = any(keyword.lower() in response_text.lower() for keyword in error_keywords)

        if is_error:
            print(f"❌ Error detected from Sickw: {response_text}")
            
            # --- AUTO REFUND LOGIC ---
            # If the user has a wallet and the transaction was marked COMPLETED, refund them.
            if transaction_obj.user and transaction_obj.status == 'COMPLETED':
                with transaction.atomic():
                    # Refund Balance
                    transaction_obj.user.balance = F('balance') + transaction_obj.amount
                    transaction_obj.user.save()
                    
                    # Mark Transaction as Refunded
                    transaction_obj.status = 'REFUNDED'
                    transaction_obj.save()
                    print(f"💰 Auto-Refunded {transaction_obj.amount} to User {transaction_obj.user.id}")
            else:
                transaction_obj.status = 'FAILED'
                transaction_obj.save()

            return False 

        # Success Case
        print("✅ Service ordered successfully on Sickw.")
        # DO NOT overwrite sickw_order_id here. It was set above.
        return True 

    except requests.RequestException as e:
        print(f"❌ Network/Connection Error: {e}")
        # Note: Network error does not mean "Failed". It might have gone through.
        # We leave it as COMPLETED but log the error so Admin checks it manually.
        return False

def sync_services_if_expired():
    """
    Sync services from Sickw API. This function should be called with 
    cache lock already set to prevent concurrent executions.
    """
    print("⏳ Syncing Services from Sickw...")
    api_key = getattr(settings, 'SICKW_API_KEY', None)
    url = "https://sickw.com/api.php"
    params = {'key': api_key, 'action': 'services'}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        service_list = data.get("Service List", [])

        if not service_list:
            return 

        # Get all existing services in one query
        existing_services = {s.service_id: s for s in Service.objects.all()}
        
        services_to_create = []
        services_to_update = []

        for item in service_list:
            service_id = str(item['service'])
            service_data = {
                'name': item['name'],
                'provider_price': item['price'],
            }
            
            if service_id in existing_services:
                # Prepare for bulk update
                service = existing_services[service_id]
                service.name = service_data['name']
                service.provider_price = service_data['provider_price']
                services_to_update.append(service)
            else:
                # Prepare for bulk create
                services_to_create.append(Service(
                    service_id=service_id,
                    **service_data
                ))
        
        # Bulk update existing services
        if services_to_update:
            Service.objects.bulk_update(services_to_update, ['name', 'provider_price'])
        
        # Bulk create new services
        if services_to_create:
            Service.objects.bulk_create(services_to_create, ignore_conflicts=True)

        print("✅ Sync Complete.")

    except Exception as e:
        print(f"⚠️ Sync Failed: {e}")    
        # Release the lock on failure so it can be retried sooner
        cache.delete('sickw_sync_lock')    

def is_valid_luhn(imei):
    if not imei.isdigit():
        return False
        
    digits = [int(d) for d in str(imei)]
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