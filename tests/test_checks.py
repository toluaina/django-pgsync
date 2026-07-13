import unittest

from django.test import override_settings

from django_pgsync.checks import check_pgsync_settings


class TestSystemChecks(unittest.TestCase):
    def test_no_pgsync_setting_is_fine(self):
        self.assertEqual(check_pgsync_settings(None), [])

    @override_settings(PGSYNC={"MODE": "wal", "REDIS_HOST": "localhost"})
    def test_valid_settings_pass(self):
        self.assertEqual(check_pgsync_settings(None), [])

    @override_settings(PGSYNC="not-a-dict")
    def test_non_dict_is_an_error(self):
        errors = check_pgsync_settings(None)
        self.assertEqual([e.id for e in errors], ["django_pgsync.E001"])

    @override_settings(PGSYNC={"MODE": "triggers"})
    def test_invalid_mode_is_an_error(self):
        errors = check_pgsync_settings(None)
        self.assertEqual([e.id for e in errors], ["django_pgsync.E002"])

    @override_settings(PGSYNC={"redis_host": "localhost"})
    def test_lowercase_key_is_a_warning(self):
        errors = check_pgsync_settings(None)
        self.assertEqual([e.id for e in errors], ["django_pgsync.W001"])

    @override_settings(PGSYNC={"CHEKPOINT_PATH": "/var/lib/pgsync"})
    def test_unknown_key_is_a_typo_warning(self):
        errors = check_pgsync_settings(None)
        self.assertEqual([e.id for e in errors], ["django_pgsync.W002"])

    @override_settings(
        PGSYNC={
            "MODE": "polling",
            "CHECKPOINT_PATH": "/var/lib/pgsync",
            "POLL_INTERVAL": 10,
            "ELASTICSEARCH_CHUNK_SIZE": 2000,
            "PG_SSLMODE": "require",
        }
    )
    def test_known_settings_pass_clean(self):
        self.assertEqual(check_pgsync_settings(None), [])


if __name__ == "__main__":
    unittest.main()
