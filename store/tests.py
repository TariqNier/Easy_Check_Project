import os
import django
import requests

# 1. Setup Django (So it can read your settings.py and .env)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'system.settings') # Change 'easy_check' to your project name
django.setup()

from django.conf import settings
from store.utils import get_kashier_auth_headers

def test_connection():
    print("--- 📡 STARTING KASHIER CONNECTION TEST ---")
    
    # Check if keys are loaded
    if not settings.KASHIER_MID:
        print("❌ ERROR: KASHIER_MID is missing from settings.")
        return

    # Prepare the URL
    url = f"{settings.KASHIER_API_URL}/v3/payment/sessions"
    
    # Get Headers
    headers = get_kashier_auth_headers()
    print(f"🔑 Using Headers: {headers}")

    # Fake Data (Just to see if they reject us or accept us)
    payload = {
        "merchantId": settings.KASHIER_MID,
        "amount": 100
    }

    try:
        # Send Request
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"\n📨 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")

        # Analyze Result
        if response.status_code == 401:
            print("\n❌ AUTH FAILED: Your Keys are wrong.")
        elif response.status_code in [200, 201, 400]:
            print("\n✅ CONNECTION SUCCESSFUL: (400 is fine here, it means Auth worked but data was fake)")
        else:
            print("\n⚠️ UNEXPECTED RESPONSE.")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_connection()