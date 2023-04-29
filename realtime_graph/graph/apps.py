from django.apps import AppConfig

import os

class GraphConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'graph'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            print("hello\n\n\n\n")

# class BrowserConfig(AppConfig):
#     name = 'browser'
    
#     def ready(self):
#         print("hello\n\n\n")
