from django.core.management.base import BaseCommand
from store.models import Transaction
from store.utils import send_guest_result_email
from django.conf import settings
import requests
import json
from datetime import datetime, timedelta
import pytz

class Command(BaseCommand):
    help = 'Checks pending Sickw orders and emails guests when done'

    def handle(self, *args, **kwargs):
        # Find transactions that are PAID (Completed) but have NO Result yet
        pending_txns = Transaction.objects.filter(
            status='COMPLETED',
            # Adjust this filter based on how your DB stores "empty" results
            service_details__api_result__isnull=True 
        )

        if not pending_txns.exists():
            self.stdout.write("No pending orders to check.")
            return

        api_key = getattr(settings, 'SICKW_API_KEY', None)
        url = "https://sickw.com/api.php"

        for txn in pending_txns:
            # Get Sickw Order ID from your saved details
            details = txn.service_details or {}
            sickw_id = details.get('sickw_order_id')
            
            if not sickw_id:
                continue

            # 🛑 TRAP DOOR: Handle Mock Orders
            if str(sickw_id).startswith("MOCK-999-"):
                self.stdout.write(f"🧪 Checking Mock Order {sickw_id}...")
                
                # 1. Check how old the transaction is
                # (Assumes txn.created_at is timezone aware)
                time_diff = datetime.now(pytz.utc) - txn.created_at
                
                # 2. If less than 5 minutes, keep waiting
                if time_diff.total_seconds() < 300: # 300 seconds = 5 minutes
                    self.stdout.write(f"   ↳ Still waiting... ({int(time_diff.total_seconds())}s / 300s)")
                    continue
                
                # 3. If 5 minutes passed, FAKE SUCCESS!
                new_result_text = "SUCCESS: MOCK_UNLOCK_CODE_123456"
                
                # Save and Send Email (Reuse your existing logic variables)
                txn.service_details['api_result'] = {'result': new_result_text}
                txn.save()
                
                # Fetch Real Service Name
                service_id = txn.service_details.get('service_id')
                service_obj = Service.objects.filter(service_id=service_id).first()
                
                if service_obj:
                    service_name = service_obj.name
                else:
                    service_name = txn.service_details.get('service_name', 'Slow Test Service')
                
                if txn.guest_email:
                    send_guest_result_email(
                        txn.guest_email,
                        txn.merchant_transaction_id,
                        service_name,
                        new_result_text
                    )
                    print(f"   📧 Test Email sent to {txn.guest_email}")
                
                continue # Skip the rest of the loop (real Sickw call)

            self.stdout.write(f"Checking Sickw ID: {sickw_id}...")

            try:
                # Ask Sickw for status
                response = requests.get(url, params={
                    'key': api_key,
                    'format': 'json',
                    'order': sickw_id # Check specific order
                })
                
                data = response.json()
                
                # Check if result is ready (Sickw usually returns 'result' key)
                result_text = data.get('result')
                
                print(f"🔎 Status for Order {sickw_id}: {result_text}")
                
                # If we got a real result (not "Pending" or "Processing")
                if result_text and "Pending" not in str(result_text):
                    
                    print(f"✅ Order {sickw_id} Finished!")
                    
                    # 1. Update Database
                    txn.service_details['api_result'] = result_text
                    txn.save()

                    # 2. Email the Guest
                    if txn.guest_email:
                        service_name = details.get('service_name', 'Service')
                        send_guest_result_email(
                            txn.guest_email,
                            txn.merchant_transaction_id,
                            service_name,
                            result_text
                        )
                        print(f"📧 Email sent to {txn.guest_email}")

            except Exception as e:
                print(f"Error checking order {sickw_id}: {e}")