"""Declarative index definitions.

Usage (in <app>/search_indexes.py)::

    from django_pgsync import PGSyncIndex, Nested
    from .models import Author, Book, Publisher, Rating

    class BookIndex(PGSyncIndex):
        model = Book
        index = "books"
        fields = ["id", "title", "isbn"]
        children = [
            Nested(Rating),                      # FK inferred: one_to_many
            Nested(Publisher, fields=["name"]),  # FK on Book: one_to_one
            Nested(Author),                      # M2M: through table inferred
        ]
"""

import typing as t


class Nested:
    """A child node in the document tree, backed by a Django model."""

    def __init__(
        self,
        model,
        *,
        fields: t.Optional[t.Sequence[str]] = None,
        exclude: t.Sequence[str] = (),
        label: t.Optional[str] = None,
        variant: str = "object",
        type: t.Optional[str] = None,
        through: t.Optional[t.Any] = None,
        foreign_key: t.Optional[dict] = None,
        children: t.Sequence["Nested"] = (),
        schema: t.Optional[str] = None,
        transform: t.Optional[dict] = None,
    ) -> None:
        self.model = model
        self.fields = fields
        self.exclude = exclude
        self.label = label
        self.variant = variant
        self.rel_type = type
        # `through` may be a Django model, a table name string, or None
        # (auto-detected when the parent declares a ManyToManyField).
        self.through = through
        self.foreign_key = foreign_key
        self.children = list(children)
        self.schema = schema
        self.transform = transform


class IndexRegistry:
    """Registry of all PGSyncIndex subclasses discovered at startup."""

    def __init__(self) -> None:
        self._indexes: t.Dict[str, t.Type["PGSyncIndex"]] = {}

    def register(self, index_cls: t.Type["PGSyncIndex"]) -> None:
        self._indexes[index_cls.get_index_name()] = index_cls

    def get(self, name: str) -> t.Type["PGSyncIndex"]:
        try:
            return self._indexes[name]
        except KeyError:
            raise LookupError(
                f"No PGSyncIndex registered for index {name!r}. "
                f"Registered indexes: {sorted(self._indexes) or 'none'}"
            ) from None

    def all(self) -> t.List[t.Type["PGSyncIndex"]]:
        return list(self._indexes.values())

    def __iter__(self):
        return iter(self._indexes.values())

    def __len__(self) -> int:
        return len(self._indexes)


registry = IndexRegistry()


class PGSyncIndexMeta(type):
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        # Register every concrete subclass that declares a model.
        if (
            bases
            and attrs.get("model") is not None
            and not attrs.get("abstract", False)
        ):
            registry.register(cls)
        return cls


class PGSyncIndex(metaclass=PGSyncIndexMeta):
    """Declarative mapping of a Django model tree to a PGSync document."""

    model = None
    abstract = False

    #: Search index name. Defaults to the model's db_table.
    index: t.Optional[str] = None
    #: Django database alias to sync from.
    database_alias: str = "default"
    #: Root columns; None means all concrete columns.
    fields: t.Optional[t.Sequence[str]] = None
    exclude: t.Sequence[str] = ()
    children: t.Sequence[Nested] = ()
    #: Postgres schema of the root table (defaults to PGSync's default).
    schema_name: t.Optional[str] = None

    # Optional PGSync document-level settings.
    plugins: t.Sequence[str] = ()
    setting: t.Optional[dict] = None
    mapping: t.Optional[dict] = None
    routing: t.Optional[str] = None

    @classmethod
    def get_index_name(cls) -> str:
        return cls.index or cls.model._meta.db_table

    @classmethod
    def get_database_name(cls) -> str:
        from django.conf import settings

        return settings.DATABASES[cls.database_alias]["NAME"]

    @classmethod
    def to_document(cls) -> dict:
        from .schema import build_document

        return build_document(cls)
