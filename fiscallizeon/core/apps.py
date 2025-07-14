from django.apps import AppConfig
# from .monkey_patch_db import patch_cursor

class CoreConfig(AppConfig):
    name = 'fiscallizeon.core'

    # def ready(self):
    #     patch_cursor()