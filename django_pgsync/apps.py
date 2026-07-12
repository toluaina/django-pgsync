from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class DjangoPGSyncConfig(AppConfig):
    name = "django_pgsync"
    verbose_name = "Django PGSync"

    def ready(self) -> None:
        # Registers the system checks.
        from . import checks  # noqa: F401

        # Import <app>/search_indexes.py from every installed app so that
        # PGSyncIndex subclasses register themselves.
        autodiscover_modules("search_indexes")
