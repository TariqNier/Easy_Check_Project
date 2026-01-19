from django.core.management.base import BaseCommand
from store.models import Transaction
from store.utils import send_guest_result_email
from django.conf import settings
import requests

class Command(BaseCommand):
    help = 'Checks status of pending Guest orders'

    def handle(self, *args, **kwargs):
        self.stdout.write("🕒 Starting Order Check...")

        # 1. Fetch Guest Orders that are Paid (COMPLETED) but have no result yet
        # We add status='COMPLETED' to ensure we don't check failed/unpaid orders
        trxns = Transaction.objects.filter(
            user=None, 
            guest_result=False, 
            status='COMPLETED'
        )
        
        if trxns.count() == 0:
            self.stdout.write("✅ No pending guest transactions found.")
            return
        
        for txn in trxns:
            sickw_id = str(txn.sickw_order_id)
            self.stdout.write(f"👉 Checking Order #{txn.id} (Sickw ID: {sickw_id})")

            # ----------------------------------------------------------
            # STEP 1: GET LATEST STATUS FROM API
            # ----------------------------------------------------------
            # You cannot rely on the old DB data. You must fetch the new status.
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
                new_result_text = data.get('result') # The fresh status from Sickw

                # ----------------------------------------------------------
                # STEP 2: CHECK IF IT IS STILL PENDING
                # ----------------------------------------------------------
                # Logic: If it is empty, or contains "Pending"/"Processing", we skip.
                is_pending = False
                if not new_result_text:
                    is_pending = True
                elif "Pending" in str(new_result_text) or "Process" in str(new_result_text):
                    is_pending = True

                if is_pending:
                    self.stdout.write(f"   ⏳ Status is still Pending. Skipping.")
                    # We skip it. Next time the cron runs, we will check API again.
                    continue  

                # ----------------------------------------------------------
                # STEP 3: IT IS DONE -> SEND EMAIL
                # ----------------------------------------------------------
                self.stdout.write(f"   🎉 Order Finished! Result: {new_result_text}")

                # A. Update Database with the new result
                txn.service_details['api_result'] = data
                
                # B. Mark as Done (So we don't check/email again)
                txn.guest_result = True
                txn.save()

                # C. Send the Email
                if txn.guest_email:
                    service_name = txn.service_details.get('service_name', 'Service')
                    self.stdout.write(f"   📧 Sending email to {txn.guest_email}...")
                    
                    try:
                        send_guest_result_email(
                            txn.guest_email,
                            txn.merchant_transaction_id,
                            service_name,
                            new_result_text
                        )
                        self.stdout.write("   ✅ Email Sent Successfully.")
                    except Exception as e:
                        self.stdout.write(f"   ❌ Failed to send email: {e}")

            except Exception as e:
                self.stdout.write(f"   ❌ Network Error: {e}")