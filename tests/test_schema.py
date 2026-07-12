import unittest

from django_pgsync.schema import (
    SchemaGenerationError,
    build_documents,
    model_columns,
)


class TestSchemaGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from testapp.models import Book

        cls.Book = Book
        cls.document = build_documents("books")[0]
        cls.nodes = cls.document["nodes"]
        cls.children = {child["table"]: child for child in cls.nodes["children"]}

    def test_document_shape(self):
        self.assertEqual(self.document["database"], "testdb")
        self.assertEqual(self.document["index"], "books")
        self.assertEqual(self.nodes["table"], "book")
        self.assertEqual(self.nodes["columns"], ["isbn", "title", "description"])

    def test_fk_child_is_one_to_many(self):
        rating = self.children["rating"]
        self.assertEqual(
            rating["relationship"],
            {"variant": "object", "type": "one_to_many"},
        )
        self.assertEqual(rating["columns"], ["value"])

    def test_one_to_one_child(self):
        detail = self.children["book_detail"]
        self.assertEqual(detail["relationship"]["type"], "one_to_one")
        self.assertEqual(detail["label"], "detail")

    def test_parent_side_fk_is_one_to_one(self):
        publisher = self.children["publisher"]
        self.assertEqual(publisher["relationship"]["type"], "one_to_one")

    def test_m2m_child_gets_through_table(self):
        author = self.children["author"]
        self.assertEqual(author["relationship"]["type"], "one_to_many")
        self.assertEqual(author["relationship"]["through_tables"], ["book_authors"])

    def test_node_keys_are_valid_pgsync_attributes(self):
        # Mirrors pgsync.constants.NODE_ATTRIBUTES / RELATIONSHIP_ATTRIBUTES
        node_attributes = {
            "base_tables",
            "children",
            "columns",
            "label",
            "primary_key",
            "relationship",
            "schema",
            "table",
            "transform",
        }
        relationship_attributes = {
            "foreign_key",
            "through_tables",
            "type",
            "variant",
        }

        def check(node):
            self.assertTrue(set(node) <= node_attributes, set(node))
            if "relationship" in node:
                self.assertTrue(set(node["relationship"]) <= relationship_attributes)
            for child in node.get("children", []):
                check(child)

        check(self.nodes)

    def test_default_columns_include_fk_column(self):
        columns = model_columns(self.Book)
        self.assertIn("publisher_id", columns)
        self.assertIn("isbn", columns)

    def test_field_name_resolves_to_column(self):
        # "publisher" (field name) resolves to "publisher_id" (column)
        self.assertEqual(
            model_columns(self.Book, fields=["publisher"]),
            ["publisher_id"],
        )

    def test_unknown_field_raises(self):
        with self.assertRaises(SchemaGenerationError):
            model_columns(self.Book, fields=["nope"])

    def test_unrelated_child_raises(self):
        from testapp.models import Author, Publisher

        from django_pgsync import Nested
        from django_pgsync.schema import build_child_node

        with self.assertRaises(SchemaGenerationError):
            build_child_node(Publisher, Nested(Author))


if __name__ == "__main__":
    unittest.main()
