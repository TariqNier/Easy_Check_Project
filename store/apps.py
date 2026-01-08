from django.apps import AppConfig


class StoreConfig(AppConfig):
    name = 'store'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        import store.signals  # noqa
