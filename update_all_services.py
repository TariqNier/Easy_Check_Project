import pandas as pd
from store.models import Service


def update_service_status_from_xlsx(file_path):
    df = pd.read_excel(file_path)

    service_names = df['Service Name'].dropna().unique()

    service_names = [name.strip() for name in service_names]
    print("Service names to activate:", service_names)
    Service.objects.filter(name__in=service_names).update(is_active=True)
    print("Service names updated:", Service.objects.filter(name__in=service_names).count())
    Service.objects.exclude(name__in=service_names).update(is_active=False)
    print("Service names updated:", Service.objects.filter(name__in=service_names).count())

    return {
        "updated_active": Service.objects.filter(is_active=True).count(),
        "updated_inactive": Service.objects.filter(is_active=False).count(),
    }


update_service_status_from_xlsx("all_servicesedited_full.xlsx")
