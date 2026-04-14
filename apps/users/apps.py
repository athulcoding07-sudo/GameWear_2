from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'apps.users'   # ✅ THIS IS THE FIX
    label = 'users' 
