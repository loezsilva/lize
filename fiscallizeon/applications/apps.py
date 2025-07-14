from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    name = 'fiscallizeon.applications'

    def ready(self):
        import fiscallizeon.applications.signals
