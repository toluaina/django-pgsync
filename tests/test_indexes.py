"""Tests for the PGSyncIndex registry and document-level settings."""

import unittest

from django_pgsync import PGSyncIndex, registry


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self._snapshot = dict(registry._indexes)

    def tearDown(self):
        registry._indexes.clear()
        registry._indexes.update(self._snapshot)

    def test_unknown_index_raises_helpful_error(self):
        with self.assertRaises(LookupError) as ctx:
            registry.get("nope")
        self.assertIn("books", str(ctx.exception))

    def test_abstract_index_is_not_registered(self):
        from testapp.models import Publisher

        class AbstractIndex(PGSyncIndex):
            abstract = True
            model = Publisher
            index = "should_not_register"

        with self.assertRaises(LookupError):
            registry.get("should_not_register")

    def test_index_name_defaults_to_db_table(self):
        from testapp.models import Publisher

        class PublisherIndex(PGSyncIndex):
            model = Publisher

        self.assertIs(registry.get("publisher"), PublisherIndex)

    def test_document_level_settings(self):
        from testapp.models import Publisher

        class FancyIndex(PGSyncIndex):
            model = Publisher
            index = "fancy"
            plugins = ["Villain"]
            setting = {"number_of_replicas": 2}
            mapping = {"properties": {"name": {"type": "keyword"}}}
            routing = "id"

        document = FancyIndex.to_document()
        self.assertEqual(document["plugins"], ["Villain"])
        self.assertEqual(document["setting"], {"number_of_replicas": 2})
        self.assertEqual(
            document["mapping"],
            {"properties": {"name": {"type": "keyword"}}},
        )
        self.assertEqual(document["routing"], "id")

    def test_document_omits_unset_optional_keys(self):
        from testapp.models import Publisher

        class PlainIndex(PGSyncIndex):
            model = Publisher
            index = "plain"

        document = PlainIndex.to_document()
        self.assertEqual(set(document), {"database", "index", "nodes"})


if __name__ == "__main__":
    unittest.main()
