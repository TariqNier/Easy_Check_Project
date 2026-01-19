from django.core.management.base import BaseCommand
from store.models import Transaction, Service
from store.utils import send_guest_result_email
from datetime import datetime, timezone
import requests

class Command(BaseCommand):
    help = 'Checks status of pending Sickw orders'

    def handle(self, *args, **kwargs):
        self.stdout.write("🕒 Starting Order Check...")

        # 1. Find all COMPLETED transactions that have a Sickw ID
        candidates = Transaction.objects.filter(
            status='COMPLETED', 
            sickw_order_id__isnull=False
        )
        
        # Filter out ones that are already 'Success' or 'Rejected'
        # (We only want Pending, Processing, or our MOCK-WAITING ones)
        pending_list = []
        for txn in candidates:
            res = txn.service_details.get('api_result', {})
            # Handle string vs dict result
            res_str = str(res.get('result', '')) if isinstance(res, dict) else str(res)
            
            # If it's NOT finished, add to list
            if "Success" not in res_str and "Rejected" not in res_str and "NotFound" not in res_str:
                pending_list.append(txn)

        self.stdout.write(f"🔎 Found {len(pending_list)} pending orders to check.")

        for txn in pending_list:
            sickw_id = str(txn.sickw_order_id)
            self.stdout.write(f"👉 Checking ID: {sickw_id} (Trx #{txn.id})")

            # ---------------------------------------------------------
            # 🚀 REAL SICKW API CHECK (For non-mock orders)
            # ---------------------------------------------------------
            api_key = "YOUR_API_KEY_HERE" # (It usually loads from settings)
            # We assume your settings/utils handles the key, or we fetch it here:
            from django.conf import settings
            api_key = settings.SICKW_API_KEY
            
            url = "https://sickw.com/api.php"
            params = {
                'key': api_key,
                'action': 'checkorder',
                'id': sickw_id,
                'format': 'json'
            }

            try:
                response = requests.get(url, params=params, timeout=20)
                data = response.json()
                new_result_text = data.get('result')

                # If the status changed from Pending -> Success/Rejected
                if new_result_text and "Pending" not in str(new_result_text) and "Process" not in str(new_result_text):
                    
                    self.stdout.write(f"   🎉 Real Order Finished! Result: {new_result_text}")
                    
                    # Update DB
                    txn.service_details['api_result'] = data
                    txn.save()

                    # Send Email
                    if txn.guest_email:
                        # Fetch correct service name logic
                        service_name = txn.service_details.get('service_name', 'Service')
                        
                        send_guest_result_email(
                            txn.guest_email,
                            txn.merchant_transaction_id,
                            service_name,
                            new_result_text
                        )
            except Exception as e:
                self.stdout.write(f"   ❌ Network Error checking Sickw: {e}")