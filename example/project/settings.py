"""Minimal settings for the django-pgsync example project.

Environment overrides:
    DEMO_DB_NAME / DEMO_DB_HOST / DEMO_DB_PORT / DEMO_DB_USER / DEMO_DB_PASSWORD
    ELASTICSEARCH_URL (default http://localhost:9200)
    OPENSEARCH=true   (set when the search backend is OpenSearch)
    PGSYNC_MODE       (default polling)
"""

import getpass
import os

SECRET_KEY = "insecure-example-key"
DEBUG = True

INSTALLED_APPS = [
    "django_pgsync",
    "bookstore",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DEMO_DB_NAME", "django_pgsync_demo"),
        "HOST": os.environ.get("DEMO_DB_HOST", "localhost"),
        "PORT": int(os.environ.get("DEMO_DB_PORT", "5432")),
        "USER": os.environ.get("DEMO_DB_USER", getpass.getuser()),
        "PASSWORD": os.environ.get("DEMO_DB_PASSWORD", ""),
    }
}

PGSYNC = {
    "MODE": os.environ.get("PGSYNC_MODE", "polling"),
    "ELASTICSEARCH_URL": os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"),
}

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
