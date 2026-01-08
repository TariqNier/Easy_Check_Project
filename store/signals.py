from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Service


@receiver([post_save, post_delete], sender=Service)
def invalidate_service_cache(sender, instance, **kwargs):
    """
    Invalidate service caches when a service is created, updated, or deleted.
    This ensures users always see up-to-date service information.
    """
    # Invalidate the service list cache
    cache.delete('service_list_active')
    
    # Invalidate individual service cache
    cache_key = f'service_{instance.service_id}'
    cache.delete(cache_key)
