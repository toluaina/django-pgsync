from django.db import models


class Publisher(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = "testapp"
        db_table = "publisher"


class Author(models.Model):
    name = models.CharField(max_length=255)
    birth_year = models.IntegerField(null=True)

    class Meta:
        app_label = "testapp"
        db_table = "author"


class Book(models.Model):
    isbn = models.CharField(max_length=13, primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    publisher = models.ForeignKey(
        Publisher, on_delete=models.CASCADE, related_name="books"
    )
    authors = models.ManyToManyField(Author, related_name="books")

    class Meta:
        app_label = "testapp"
        db_table = "book"


class Rating(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    value = models.IntegerField()

    class Meta:
        app_label = "testapp"
        db_table = "rating"


class BookDetail(models.Model):
    book = models.OneToOneField(Book, on_delete=models.CASCADE)
    page_count = models.IntegerField()

    class Meta:
        app_label = "testapp"
        db_table = "book_detail"
