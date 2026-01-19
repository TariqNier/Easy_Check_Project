from django.core.management.base import BaseCommand
from store.models import Transaction
from store.utils import send_guest_result_email
from datetime import datetime, timezone
import requests

class Command(BaseCommand):
    help = 'Checks status of pending Sickw orders'

    def handle(self, *args, **kwargs):
        self.stdout.write("🕒 Starting Order Check...")

        # 1. Find all COMPLETED transactions (Payment is done)
        # Also includes RETRY orders (network failures that need retry)
        candidates = Transaction.objects.filter(
            status='COMPLETED', 
            sickw_order_id__isnull=False
        )
        
        pending_list = []
        for txn in candidates:
            res = txn.service_details.get('api_result', {})
            # Handle string vs dict result
            res_str = str(res.get('result', '')) if isinstance(res, dict) else str(res)
            
            # =========================================================
            # 🛑 THE FIX: STRICT PENDING CHECK
            # =========================================================
            # We ONLY process orders if the result explicitly says "Pending".
            # If it says "Error...", "Success...", "Rejected...", or "Code:...", 
            # we consider it FINAL and skip it.
            if "Pending" in res_str or "Processing" in res_str or not res_str:
                pending_list.append(txn)
            # =========================================================

        self.stdout.write(f"🔎 Found {len(pending_list)} pending orders to check.")

        for txn in pending_list:
            sickw_id = str(txn.sickw_order_id)
            self.stdout.write(f"👉 Checking ID: {sickw_id} (Trx #{txn.id})")

            # ---------------------------------------------------------
            # � RETRY HANDLER: Network Timeout Recovery
            # ---------------------------------------------------------
            if sickw_id.startswith("RETRY-"):
                self.stdout.write(f"🔄 Retrying failed API call for Trx #{txn.id}...")
                
                # Import the order function to retry
                from store.utils import place_sickw_order
                
                # Retry the Sickw API call
                success = place_sickw_order(txn)
                
                if success:
                    self.stdout.write(f"   ✅ Retry successful!")
                    txn.refresh_from_db()
                    
                    # Check if instant result, send email if guest
                    if txn.guest_email:
                        api_result = txn.service_details.get('api_result', {})
                        result_text = api_result.get('result', '') if isinstance(api_result, dict) else str(api_result)
                        
                        if result_text and "Pending" not in str(result_text):
                            from store.models import Service
                            service_id = txn.service_details.get('service_id')
                            service_obj = Service.objects.filter(service_id=service_id).first()
                            service_name = service_obj.name if service_obj else 'Service'
                            
                            send_guest_result_email(
                                txn.guest_email,
                                txn.merchant_transaction_id,
                                service_name,
                                result_text
                            )
                else:
                    self.stdout.write(f"   ❌ Retry still failing. Will try again next run.")
                
                continue
            # ---------------------------------------------------------
            
            # ---------------------------------------------------------
            # �🛑 TRAP DOOR: 1-MINUTE TIMER LOGIC (Mock Service)
            # ---------------------------------------------------------
            if sickw_id.startswith("MOCK-WAITING-"):
                
                # 1. Calculate Time
                if txn.created_at.tzinfo:
                    now = datetime.now(timezone.utc)
                    created_at = txn.created_at
                else:
                    now = datetime.now()
                    created_at = txn.created_at

                elapsed = (now - created_at).total_seconds()
                wait_time = 60 # 60 Seconds

                # 2. Still Waiting?
                if elapsed < wait_time:
                    remaining = int(wait_time - elapsed)
                    self.stdout.write(f"   ⏳ Timer Running... {remaining}s remaining.")
                    continue 
                
                # 3. Time Up! Finish it.
                self.stdout.write(f"   ✅ Time is up! Completing Mock Order.")
                
                fake_code = "SUCCESS_CODE_1_MINUTE_TEST"
                
                # Update DB (This removes 'Pending', so loop will stop next time)
                txn.service_details['api_result'] = {'result': fake_code}
                
                # Rename ID just to be safe
                txn.sickw_order_id = f"MOCK-DONE-{txn.id}"
                txn.save()
                
                # Send Email
                if txn.guest_email:
                    service_name = txn.service_details.get('service_name', 'Test Service')
                    self.stdout.write(f"   📧 Sending Email to {txn.guest_email}...")
                    try:
                        send_guest_result_email(
                            txn.guest_email,
                            txn.merchant_transaction_id,
                            service_name,
                            fake_code
                        )
                    except Exception as e:
                        self.stdout.write(f"   ❌ Email Failed: {e}")
                
                continue 
            # ---------------------------------------------------------


            # ---------------------------------------------------------
            # 🚀 REAL SICKW API CHECK
            # ---------------------------------------------------------
            # We fetch the key safely
            from django.conf import settings
            api_key = getattr(settings, 'SICKW_API_KEY', None)
            
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

                # Only update if the result is valid and NO LONGER PENDING
                if new_result_text and "Pending" not in str(new_result_text) and "Process" not in str(new_result_text):
                    
                    self.stdout.write(f"   🎉 Real Order Finished! Result: {new_result_text}")
                    
                    # Update DB (This removes 'Pending', so loop stops next time)
                    txn.service_details['api_result'] = data
                    txn.save()

                    # Send Email
                    if txn.guest_email:
                        service_name = txn.service_details.get('service_name', 'Service')
                        send_guest_result_email(
                            txn.guest_email,
                            txn.merchant_transaction_id,
                            service_name,
                            new_result_text
                        )
            except Exception as e:
                self.stdout.write(f"   ❌ Network Error checking Sickw: {e}")