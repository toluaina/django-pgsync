from django_pgsync import Nested, PGSyncIndex

from .models import Author, Book, Publisher, Rating


class BookIndex(PGSyncIndex):
    model = Book
    index = "demo-books"
    fields = ["isbn", "title", "description"]
    children = [
        # label controls the key in the document; relationships are inferred
        Nested(Rating, fields=["value"], label="ratings"),  # FK -> one_to_many
        Nested(Publisher, fields=["name"], label="publisher"),  # -> one_to_one
        Nested(Author, fields=["name"], label="authors"),  # M2M via through
    ]
