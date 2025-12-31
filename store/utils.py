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
    print(f"🔄 Attempting to place Sickw order for Trx #{transaction_obj.id}...")

    details = transaction_obj.service_details or {}
    service_id = details.get('service_id')
    imei = details.get('imei')

    if not service_id or not imei:
        print("❌ Error: Missing Service ID or IMEI.")
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
                print(f"❌ Error detected in Sickw response: {keyword}")
                return False 

        # 4. If no errors were found
        print("✅ Service ordered successfully")
        transaction_obj.sickw_order_id = service_id
        transaction_obj.save()
        return True  # Return True because it succeeded

    except requests.RequestException as e:
        print(f"❌ Network/Connection Error: {e}")
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
  
  
  
  
  
    
# --- KASHIER CAPTURE / VOID LOGIC ---

# 🔥 HELPER: Get the correct FEP URL (Fixes the "Expecting value" error)
def get_kashier_fep_url():
    if "test" in settings.KASHIER_API_URL:
        return "https://test-fep.kashier.io"
    return "https://fep.kashier.io"

def capture_payment(transaction):
    base_url = get_kashier_fep_url()
    url = f"{base_url}/v3/orders/{transaction.merchant_transaction_id}"
    
    headers = {
        "Authorization": settings.KASHIER_SECRET_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "apiOperation": "CAPTURE",
        "transaction": { 
            "amount": float(transaction.amount)
        }
    }
    
    response = requests.put(url, json=payload, headers=headers)
    return response
    
    # try:
    #     print(f"💰 Sending Capture Request to: {url}")
    #     response = requests.put(url, json=payload, headers=headers)
    #     print(f"🔍 DEBUG KASHIER RAW RESPONSE: {response.text}")
    #     # Safety Check
    #     if response.status_code not in [200, 201]:
    #          print(f"❌ Capture API Error {response.status_code}: {response.text}")
    #          return False

    #     data = response.json()
        
    #     result_status = data.get('response', {}).get('status')
    #     if result_status == 'CAPTURED':
    #         print(f"✅ Payment Captured for #{transaction.id}")
    #         return True
            
    #     print(f"❌ Capture Failed. API Status: {result_status}")
    #     return False
        
    # except Exception as e:
    #     print(f"❌ Capture Exception: {e}")
    #     return False

def void_payment(transaction):
    """
    Step 3B: VOID.
    Method: PUT
    URL: /v3/orders/{merchant_order_id}
    """
    # 🔥 USE FEP URL
    base_url = get_kashier_fep_url()
    url = f"{base_url}/v3/orders/{transaction.merchant_transaction_id}"
    
    headers = {
        "Authorization": settings.KASHIER_SECRET_KEY,
        "Content-Type": "application/json"
    }
    
    if not transaction.kashier_transaction_id:
        print(f"❌ Cannot Void: Missing 'kashier_transaction_id' (TX-...)")
        return False

    payload = {
        "apiOperation": "VOID",
        "transaction": {
            "amount": float(transaction.amount),
            "targetTransactionId": transaction.kashier_transaction_id
        }
    }
    
    try:
        print(f"💨 Sending Void Request to: {url}")
        response = requests.put(url, json=payload, headers=headers)
        
        # Safety Check
        if response.status_code not in [200, 201]:
             print(f"❌ Void API Error {response.status_code}: {response.text}")
             return False
        
        data = response.json()
        
        result_status = data.get('response', {}).get('status')
        if result_status == 'CANCELLED':
            print(f"✅ Payment Voided for #{transaction.id}")
            return True
            
        print(f"❌ Void Failed. API Status: {result_status}")
        return False
        
    except Exception as e:
        print(f"❌ Void Exception: {e}")
        return False