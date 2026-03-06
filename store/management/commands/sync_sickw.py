# store/management/commands/sync_sickw.py
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from store.models import Service


class Command(BaseCommand):
    help = 'Sync services and prices from Sickw API'

    def handle(self, *args, **kwargs):
        api_key = getattr(settings, 'SICKW_API_KEY', None)

        # Changed to GET request params
        url = "https://sickw.com/api.php"
        params = {
            'key': api_key,
            'action': 'services'
        }

        try:

            response = requests.get(url, params=params)

            try:
                data = response.json()
            except ValueError:
                self.stdout.write(self.style.ERROR(f" API Error: {response.text}"))
                return

            service_list = data.get("Service List", [])

            if not service_list:
                self.stdout.write(self.style.ERROR(" No services found. (Check if your API Key is correct)"))
                return

            # Update Database
            count_new = 0
            count_updated = 0

            for item in service_list:
                obj, created = Service.objects.update_or_create(
                    service_id=item['service'],
                    defaults={
                        'name': item['name'],
                        'provider_price': item['price'],
                    }
                )
                if created:
                    count_new += 1
                else:
                    count_updated += 1

            self.stdout.write(self.style.SUCCESS(f" Sync Complete! Added {count_new}, Updated {count_updated}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f" Connection Error: {str(e)}"))
