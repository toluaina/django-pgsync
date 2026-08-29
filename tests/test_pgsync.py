import unittest


class PGSyncCompatibilityTests(unittest.TestCase):
    def test_supported_pgsync_apis_are_importable(self):
        """Smoke-test the public APIs used by commands and Celery tasks."""
        from pgsync.search_client import SearchClient
        from pgsync.sync import Sync

        self.assertTrue(callable(SearchClient))
        self.assertTrue(callable(Sync))
