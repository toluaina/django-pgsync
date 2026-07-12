"""Tests for explicit Nested(...) overrides and deeper nesting."""

import unittest

from django_pgsync import Nested
from django_pgsync.schema import build_child_node, model_columns


class TestColumnSelection(unittest.TestCase):
    def test_explicit_fields_keep_declared_order(self):
        from testapp.models import Book

        self.assertEqual(
            model_columns(Book, fields=["title", "isbn"]),
            ["title", "isbn"],
        )

    def test_duplicate_selection_is_deduped(self):
        from testapp.models import Book

        # field name and column name for the same field
        self.assertEqual(
            model_columns(Book, fields=["publisher", "publisher_id"]),
            ["publisher_id"],
        )

    def test_exclude_by_field_or_column_name(self):
        from testapp.models import Book

        self.assertEqual(
            model_columns(Book, exclude=["description", "publisher"]),
            ["isbn", "title"],
        )


class TestNestedOverrides(unittest.TestCase):
    def test_relationship_type_override(self):
        from testapp.models import Book, Publisher

        node = build_child_node(Book, Nested(Publisher, type="one_to_many"))
        self.assertEqual(node["relationship"]["type"], "one_to_many")

    def test_through_as_table_name(self):
        from testapp.models import Author, Book

        node = build_child_node(Book, Nested(Author, through="custom_join"))
        self.assertEqual(node["relationship"]["through_tables"], ["custom_join"])

    def test_through_as_model(self):
        from testapp.models import Author, Book

        node = build_child_node(Book, Nested(Author, through=Book.authors.through))
        self.assertEqual(node["relationship"]["through_tables"], ["book_authors"])

    def test_foreign_key_passthrough(self):
        from testapp.models import Book, Rating

        foreign_key = {"parent": ["isbn"], "child": ["book_id"]}
        node = build_child_node(Book, Nested(Rating, foreign_key=foreign_key))
        self.assertEqual(node["relationship"]["foreign_key"], foreign_key)

    def test_schema_and_transform_passthrough(self):
        from testapp.models import Book, Rating

        transform = {"rename": {"value": "score"}}
        node = build_child_node(
            Book, Nested(Rating, schema="public", transform=transform)
        )
        self.assertEqual(node["schema"], "public")
        self.assertEqual(node["transform"], transform)

    def test_grandchild_nesting(self):
        from testapp.models import Book, Publisher, Rating

        node = build_child_node(
            Publisher,
            Nested(
                Book,
                fields=["isbn"],
                children=[Nested(Rating, fields=["value"])],
            ),
        )
        self.assertEqual(node["table"], "book")
        # Book has an FK to Publisher: one publisher, many books
        self.assertEqual(node["relationship"]["type"], "one_to_many")
        (grandchild,) = node["children"]
        self.assertEqual(grandchild["table"], "rating")
        self.assertEqual(grandchild["relationship"]["type"], "one_to_many")


if __name__ == "__main__":
    unittest.main()
