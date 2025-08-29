from django.apps import AppConfig

class ProfilePageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'profile_page'

    def ready(self):
        import profile_page.signals
