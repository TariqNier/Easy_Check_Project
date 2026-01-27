from django.core.management.base import BaseCommand
from store.models import Transaction
from store.utils import send_guest_result_email
from django.conf import settings
import requests

class Command(BaseCommand):
    help = 'Checks status of pending orders (Updates Users, Emails Guests)'

    def handle(self, *args, **kwargs):
        self.stdout.write("🕒 Starting Order Check...")

        # 1. Fetch ALL Paid & Unprocessed orders (Both Guests and Users)
        # We rely on 'guest_result=False' as meaning "Not Finalized Yet"
        trxns = Transaction.objects.filter(
            status='COMPLETED', 
            guest_result=False, 
            sickw_order_id__isnull=False
        )
        
        if trxns.count() == 0:
            self.stdout.write("✅ No pending transactions found.")
            return
        
        for txn in trxns:
            sickw_id = str(txn.sickw_order_id)
            self.stdout.write(f"👉 Checking Order #{txn.id} (Sickw ID: {sickw_id})")

            # 🛡️ SAFETY CHECK 1: Do we ALREADY have a result?
            # If we have a result that is NOT "Pending" and NOT an "Error", we are done.
            current_data = txn.service_details.get('api_result', {})
            # Handle case where result might be a string or a dict
            if isinstance(current_data, dict):
                current_text = str(current_data.get('result', ''))
            else:
                current_text = str(current_data)

            # If the current result is long (likely a description), it is valid.
            if current_text and len(current_text) > 20 and "Pending" not in current_text and "Error" not in current_text:
                self.stdout.write(f"   ✅ Order #{txn.id} already has a valid result. Marking as DONE.")
                txn.guest_result = True
                txn.save()
                continue # Skip the API call completely

            # 🛡️ SAFETY CHECK 2: Validate ID before calling
            if not sickw_id or "RETRY" in sickw_id or sickw_id == "None":
                self.stdout.write(f"   ⚠️ Skipping invalid Sickw ID: {sickw_id}")
                continue

            # --- API CHECK ---
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

                # --- PENDING CHECK ---
                is_pending = False
                res_str = str(new_result_text)
                if not new_result_text:
                    is_pending = True
                elif "Pending" in res_str or "Process" in res_str:
                    is_pending = True

                if is_pending:
                    self.stdout.write(f"   ⏳ Still Pending. Skipping.")
                    continue  

                # --- IT IS FINISHED ---
                self.stdout.write(f"   🎉 Order Finished! Result: {new_result_text}")

                # 1. Update the Data (So user sees it in dashboard)
                txn.service_details['api_result'] = data
                txn.save()

                # --- LOGIC SPLIT: USER vs GUEST ---
                
                if txn.user:
                    # CASE A: REGISTERED USER
                    # Just mark it as done so we don't check it again.
                    # They will see the result when they login.
                    self.stdout.write("   👤 Registered User: Updated DB, skipping email.")
                    txn.guest_result = True
                    txn.save()
                    
                else:
                    # CASE B: GUEST
                    # Must send email because they have no dashboard.
                    if txn.guest_email:
                        self.stdout.write(f"   📧 Guest User: Sending email to {txn.guest_email}...")
                        try:
                            service_name = txn.service_details.get('service_name', 'Service')
                            send_guest_result_email(
                                txn.guest_email,
                                txn.merchant_transaction_id,
                                service_name,
                                new_result_text
                            )
                            self.stdout.write("   ✅ Email Sent!")
                            
                            # ONLY Mark as done if email succeeded
                            txn.guest_result = True
                            txn.save()
                        except Exception as e:
                            self.stdout.write(f"   ❌ Email Failed (Will Retry): {e}")
                    else:
                        # Edge case: Guest with no email? Mark done to avoid loop.
                        txn.guest_result = True
                        txn.save()

            except Exception as e:
                self.stdout.write(f"   ❌ Network/API Error: {e}")