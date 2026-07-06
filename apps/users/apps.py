from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'apps.users'
    label = 'users'

    def ready(self):
        # Import signal handlers
        import apps.users.signals  # noqa: F401
