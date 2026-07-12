from django_pgsync import Nested, PGSyncIndex

from .models import Author, Book, BookDetail, Publisher, Rating


class BookIndex(PGSyncIndex):
    model = Book
    index = "books"
    fields = ["isbn", "title", "description"]
    children = [
        Nested(Rating, fields=["value"]),
        Nested(BookDetail, fields=["page_count"], label="detail"),
        Nested(Publisher, fields=["id", "name"]),
        Nested(Author, fields=["id", "name"]),
    ]
