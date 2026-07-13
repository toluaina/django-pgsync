from django.core.management.base import BaseCommand

from bookstore.models import Author, Book, Publisher, Rating

BOOKS = [
    {
        "isbn": "9780385474542",
        "title": "Things Fall Apart",
        "description": "A classic of African literature.",
        "publisher": "Heinemann",
        "authors": [("Chinua Achebe", 1930)],
        "ratings": [5, 4],
    },
    {
        "isbn": "9780393320077",
        "title": "Ake: The Years of Childhood",
        "description": "Memoir of a Nigerian childhood.",
        "publisher": "Rex Collings",
        "authors": [("Wole Soyinka", 1934)],
        "ratings": [5],
    },
    {
        "isbn": "9780441172719",
        "title": "Dune",
        "description": "Politics, religion and giant sandworms.",
        "publisher": "Chilton Books",
        "authors": [("Frank Herbert", 1920)],
        "ratings": [5, 5, 4],
    },
]


class Command(BaseCommand):
    help = "Seed the bookstore with demo data (idempotent)."

    def handle(self, *args, **options):
        for entry in BOOKS:
            publisher, _ = Publisher.objects.get_or_create(name=entry["publisher"])
            book, created = Book.objects.update_or_create(
                isbn=entry["isbn"],
                defaults={
                    "title": entry["title"],
                    "description": entry["description"],
                    "publisher": publisher,
                },
            )
            authors = [
                Author.objects.get_or_create(name=name, defaults={"birth_year": year})[
                    0
                ]
                for name, year in entry["authors"]
            ]
            book.authors.set(authors)
            if created:
                for value in entry["ratings"]:
                    Rating.objects.create(book=book, value=value)
        self.stdout.write(self.style.SUCCESS(f"Seeded {Book.objects.count()} books"))
