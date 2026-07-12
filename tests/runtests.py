#!/usr/bin/env python
"""Standalone test runner: configures a minimal Django project and runs
the unittest suite. Usage: python tests/runtests.py"""

import os
import sys
import unittest

import django
from django.conf import settings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # so `testapp` is importable
sys.path.insert(0, os.path.dirname(HERE))  # so `django_pgsync` is importable

settings.configure(
    INSTALLED_APPS=[
        "django_pgsync",
        "testapp",
    ],
    # sqlite avoids needing psycopg installed; schema generation only
    # reads model metadata and the database NAME, never a connection.
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "testdb",
        }
    },
    USE_TZ=True,
)
django.setup()

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(HERE)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
