import os
import unittest

from django.test import override_settings

from django_pgsync.conf import (
    DEFAULT_MODE,
    RESERVED_KEYS,
    export_pgsync_env,
    get_mode,
    mode_flags,
)


class TestMode(unittest.TestCase):
    def test_default_mode_is_polling(self):
        self.assertEqual(get_mode(), "polling")
        self.assertEqual(DEFAULT_MODE, "polling")

    @override_settings(PGSYNC={"MODE": "wal"})
    def test_mode_override(self):
        self.assertEqual(get_mode(), "wal")

    @override_settings(PGSYNC={"MODE": "triggers"})
    def test_invalid_mode_raises(self):
        with self.assertRaises(RuntimeError):
            get_mode()

    def test_mode_flags(self):
        self.assertEqual(mode_flags("polling"), {"polling": True, "wal": False})
        self.assertEqual(mode_flags("wal"), {"polling": False, "wal": True})
        self.assertEqual(mode_flags("event"), {"polling": False, "wal": False})

    def test_mode_is_reserved_not_exported(self):
        self.assertIn("MODE", RESERVED_KEYS)


PG_DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "appdb",
        "HOST": "db.internal",
        "PORT": 5433,
        "USER": "app",
        "PASSWORD": "secret",
    }
}

MYSQL_DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "appdb",
        "HOST": "mysql.internal",
        "USER": "app",
        "PASSWORD": "secret",
    }
}


class TestExportEnv(unittest.TestCase):
    """export_pgsync_env writes to os.environ; snapshot and restore it."""

    def setUp(self):
        self._environ = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._environ)

    @override_settings(DATABASES=PG_DATABASES)
    def test_postgres_credentials_exported(self):
        export_pgsync_env()
        self.assertEqual(os.environ["PG_HOST"], "db.internal")
        self.assertEqual(os.environ["PG_PORT"], "5433")
        self.assertEqual(os.environ["PG_USER"], "app")
        self.assertEqual(os.environ["PG_PASSWORD"], "secret")
        self.assertNotIn("PG_DRIVER", os.environ)

    @override_settings(DATABASES=MYSQL_DATABASES)
    def test_mysql_sets_driver_and_default_port(self):
        export_pgsync_env()
        self.assertEqual(os.environ["PG_DRIVER"], "pymysql")
        self.assertEqual(os.environ["PG_PORT"], "3306")
        self.assertEqual(os.environ["PG_HOST"], "mysql.internal")

    def test_unsupported_engine_raises(self):
        # The test settings use sqlite by default.
        with self.assertRaises(RuntimeError):
            export_pgsync_env()

    @override_settings(
        DATABASES=PG_DATABASES,
        PGSYNC={
            "MODE": "wal",
            "ELASTICSEARCH_URL": "http://search:9200",
            "OPENSEARCH": True,
            "USE_ASYNC": False,
        },
    )
    def test_pgsync_settings_exported_except_reserved(self):
        export_pgsync_env()
        self.assertEqual(os.environ["ELASTICSEARCH_URL"], "http://search:9200")
        self.assertEqual(os.environ["OPENSEARCH"], "true")
        self.assertEqual(os.environ["USE_ASYNC"], "false")
        self.assertNotIn("MODE", os.environ)

    @override_settings(DATABASES=PG_DATABASES)
    def test_existing_environment_wins(self):
        os.environ["PG_PASSWORD"] = "from-vault"
        export_pgsync_env()
        self.assertEqual(os.environ["PG_PASSWORD"], "from-vault")


if __name__ == "__main__":
    unittest.main()
