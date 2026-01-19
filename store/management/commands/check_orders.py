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

            # =========================================================
            # 🛑 TRAP DOOR: 1-MINUTE TIMER LOGIC
            # =========================================================
            if sickw_id.startswith("MOCK-WAITING-"):
                
                # 1. Calculate time elapsed safely (Timezone Aware)
                if txn.created_at.tzinfo:
                    now = datetime.now(timezone.utc)
                    created_at = txn.created_at
                else:
                    now = datetime.now()
                    created_at = txn.created_at

                elapsed = (now - created_at).total_seconds()
                wait_time = 60 # 60 Seconds (1 Minute)

                # 2. Check Timer
                if elapsed < wait_time:
                    remaining = int(wait_time - elapsed)
                    self.stdout.write(f"   ⏳ Timer Running... {remaining}s remaining.")
                    continue # Skip to next order
                
                # 3. TIME IS UP! Finish the order.
                self.stdout.write(f"   ✅ Time is up! ({int(elapsed)}s passed). Completing order now.")
                
                fake_code = "SUCCESS_CODE_1_MINUTE_TEST"
                
                # Update Database
                txn.service_details['api_result'] = {'result': fake_code}
                # Change ID so we don't process it again
                txn.sickw_order_id = f"MOCK-DONE-{txn.id}"
                txn.save()
                
                # Send Email
                if txn.guest_email:
                    service_name = txn.service_details.get('service_name', 'Test Service')
                    self.stdout.write(f"   📧 Sending Result Email to {txn.guest_email}...")
                    
                    try:
                        send_guest_result_email(
                            txn.guest_email,
                            txn.merchant_transaction_id,
                            service_name,
                            fake_code
                        )
                        self.stdout.write("   ✅ Email Sent!")
                    except Exception as e:
                        self.stdout.write(f"   ❌ Email Failed: {e}")
                
                continue # Done with this order!
            # =========================================================


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