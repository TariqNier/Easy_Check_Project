from datetime import datetime
import json
import os
import requests
import hmac
import hashlib
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from .models import Service
from django.core.mail import send_mail

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
    
    # Extract ID
    raw_id = details.get('service_id')
    service_id = str(raw_id).strip() if raw_id is not None else None
    
    if raw_id=="999":
        print("⚠️ Detected Test Service ID '999'. Skipping real order.")
        return True
    
    return "SKIPPED"
    
    
    # -----------------------------------------
    # FIX: Ensure Service Name is Saved
    # -----------------------------------------
    # We look up the real name from the DB and save it to service_details
    # so emails never say "Unknown Service".
    if raw_id:
        try:
            # Try to find by Service ID or Primary Key to get the name
            svc = Service.objects.filter(service_id=raw_id).first()
            if not svc and str(raw_id).isdigit():
                # Fallback: maybe it's a Primary Key?
                svc = Service.objects.filter(pk=raw_id).first()
            
            if svc:
                transaction_obj.service_details['service_name'] = svc.name
                transaction_obj.save(update_fields=['service_details'])
                print(f"✅ Fixed Service Name: {svc.name}")
                
                # OPTIONAL: If the frontend sent a PK (e.g. 94) instead of the Real ID,
                # we can swap it here to ensure the API call works.
                # If you want to rely purely on frontend sending the correct ID, comment this line out:
                service_id = str(svc.service_id).strip() 

        except Exception as e:
            print(f"⚠️ Could not fix service name: {e}")
    # -----------------------------------------

    if not service_id:
        print("❌ Error: Missing Service ID.")
        return False

    # Extract IMEI/Serial
    imei = details.get('imei')
    serial = details.get('serial')

    print(f"🚀 Sending Real Order to Sickw: {service_id}...")

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
    elif serial:
        params['imei'] = serial

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
           "IMEI is Wrong", 
            "IMEI or SN is Wrong",
            "Error E02",
            "Invalid",
            "Not Found", 
            "Error E01", 
            "Rejected", 
            "Not supported", 
            "Insufficient Funds", 
            "Service is Down", 
            "Service ID is Wrong"
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
        return True 

    except requests.RequestException as e:
        print(f"❌ Network/Connection Error: {e}")
        return False


def load_descriptions_from_file():
    """
    Helper function to read the descriptions.json file
    located in the same folder as this script (store/descriptions.json).
    """
    try:
        # Get path to store/descriptions.json
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'descriptions.json')
        
        if not os.path.exists(json_path):
            print(f"⚠️ Descriptions file missing at: {json_path}")
            return {}

        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        print(f"❌ Error reading descriptions.json: {e}")
        return {}


def sync_services_if_expired():
    # Cache lock prevents spamming the API on every page load
    if cache.get('sickw_sync_lock'):
        return 
    print("⏳ Syncing Services from Sickw...")
    
    # 1. Load your custom descriptions first
    custom_descriptions = load_descriptions_from_file()
    
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
            svc_id = str(item['service'])
            sickw_name = item['name']
            sickw_price = item['price']
            
            # Lookup description in your loaded JSON (default to empty string if missing)
            custom_desc = custom_descriptions.get(svc_id, "")

            # 2. Try to find the service by ID or Create it
            service_obj, created = Service.objects.get_or_create(
                service_id=svc_id,
                defaults={
                    # This runs ONLY if a new service is created
                    'name': sickw_name,
                    'provider_price': sickw_price,
                    'description': custom_desc, # Use description from file
                    'is_active': True
                }
            )

            # 3. If it ALREADY existed, handle updates
            if not created:
                needs_save = False
                
                # A. Update Price (Always keep this fresh)
                if str(service_obj.provider_price) != str(sickw_price):
                    service_obj.provider_price = sickw_price
                    needs_save = True
                
                # B. Force Update Description 
                # If your JSON file has a description, we enforce it in the DB.
                # This ensures the website always matches your file.
                if custom_desc and service_obj.description != custom_desc:
                    service_obj.description = custom_desc
                    needs_save = True
                
                if needs_save:
                    service_obj.save(update_fields=['provider_price', 'description'])

        # Set lock for 6 hours (21600 seconds)
        cache.set('sickw_sync_lock', True, timeout=21600) 
        print("✅ Sync Complete.")

    except Exception as e:
        print(f"⚠️ Sync Failed: {e}")

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


def send_guest_confirmation_email(email, order_id, service_name):
    """Sent immediately after payment."""
    subject = f"Order Received: #{order_id}"
    message = f"""
    Hello!
    
    We have received your payment for: {service_name}.
    Your order is currently processing.
    
    We will email you the result immediately once it is ready.
    
    Order ID: {order_id}
    """
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")

def send_guest_result_email(email, order_id, service_name, result_text):
    """Sent by the Cron Job when Sickw finishes."""
    
    # 1. Create the clean link (Hardcoded IP as requested)
    result_link = f"http://158.220.126.228:3000/result/{order_id}"
    
    subject = f"Result Ready: Order #{order_id}"
    
    # 2. Send Link instead of raw result text
    message = f"""
    Hello!
    
    Your order for {service_name} is complete.
    
    Please click the link below to view your full result:
    
    {result_link}
    
    --------------------------------------------------
    Thank you for using our service.
    """
    
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
    except Exception as e:
        print(f"Failed to send result email: {e}")