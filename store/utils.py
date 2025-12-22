#store/utils.py
import os
import requests
from django.conf import settings

# We load the key here. If it's missing, the code will know.
SICKW_API_KEY = os.environ.get('SICKW_API_KEY')

def check_imei_on_sickw(imei, service_id):


    if not SICKW_API_KEY:
        return {'success': False, 'error': 'Server Misconfiguration: No API Key found.'}

    # 2. Prepare the URL
    url = "https://sickw.com/api.php"
    params = {
        'key': SICKW_API_KEY,
        'service': service_id,
        'imei': imei,
        'format': 'json'  
    }

   
    try:
        response = requests.get(url, params=params, timeout=10)
      
        if response.status_code != 200:
            return {'success': False, 'error': f"Sickw Error: {response.status_code}"}

    
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
    
    
 