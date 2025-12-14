#store/utils.py
import os
import requests
from django.conf import settings

# We load the key here. If it's missing, the code will know.
SICKW_API_KEY = os.environ.get('SICKW_API_KEY')

def check_imei_on_sickw(imei, service_id):
    """
    Talks to Sickw.com to check an IMEI.
    
    Args:
        imei (str): The phone's serial number.
        service_id (str): The ID of the service (e.g., "10" for Bronze).
        
    Returns:
        dict: { 'success': True, 'result': 'Clean' } OR { 'success': False, 'error': 'Service Down' }
    """
    
    # 1. Safety Check: Do we have an API Key?
    if not SICKW_API_KEY:
        return {'success': False, 'error': 'Server Misconfiguration: No API Key found.'}

    # 2. Prepare the URL
    url = "https://sickw.com/api.php"
    params = {
        'key': SICKW_API_KEY,
        'service': service_id,
        'imei': imei,
        'format': 'json'  # We ask for JSON because it's easier to read than text
    }

    # 3. Send the Request (The dangerous part)
    try:
        # timeout=10 means: "If Sickw ignores us for 10 seconds, hang up."
        # This prevents your site from freezing if their site is slow.
        response = requests.get(url, params=params, timeout=10)
        
        # 4. Check if the internet connection worked
        if response.status_code != 200:
            return {'success': False, 'error': f"Sickw Error: {response.status_code}"}

        # 5. Parse the Data
        data = response.json()
        
        # Sickw usually sends: {"status": "success", "result": "..."}
        if data.get('status') == 'error':
             # Example: "Insufficient funds" or "Invalid IMEI"
            return {'success': False, 'error': data.get('result', 'Unknown Error')}

        return {'success': True, 'result': data.get('result')}

    except requests.exceptions.RequestException as e:
        # This runs if the internet is down or Sickw is completely crashed.
        # We return False so we know NOT to charge the user.
        return {'success': False, 'error': "Service Unavailable (Connection Error)"}
    
    
    
