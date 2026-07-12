import importlib.util
import unittest

HAS_CELERY = importlib.util.find_spec("celery") is not None


class TestTasksImport(unittest.TestCase):
    @unittest.skipIf(HAS_CELERY, "celery is installed")
    def test_import_without_celery_gives_install_hint(self):
        with self.assertRaises(ImportError) as ctx:
            import django_pgsync.tasks  # noqa: F401
        self.assertIn("django-pgsync[celery]", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
