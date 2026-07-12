"""Generate PGSync schema documents from Django model metadata.

Django models already encode everything a PGSync schema needs: tables,
columns, primary/foreign keys, one-to-one links and many-to-many through
tables. This module walks a PGSyncIndex declaration and emits the
equivalent PGSync schema JSON.
"""

import typing as t

from .indexes import Nested, PGSyncIndex, registry

ONE_TO_ONE = "one_to_one"
ONE_TO_MANY = "one_to_many"


class SchemaGenerationError(Exception):
    pass


def model_columns(
    model,
    fields: t.Optional[t.Sequence[str]] = None,
    exclude: t.Sequence[str] = (),
) -> t.List[str]:
    """Resolve a field selection to database column names.

    Accepts either Django field names ("publisher") or column names
    ("publisher_id"). Defaults to all concrete columns on the table.
    Explicit selections keep the user's declared order.
    """
    concrete = list(model._meta.concrete_fields)
    if fields is None:
        selected = concrete
    else:
        by_key = {}
        for field in concrete:
            by_key[field.name] = field
            by_key[field.column] = field
        missing = [name for name in fields if name not in by_key]
        if missing:
            raise SchemaGenerationError(
                f"Unknown fields {missing} on model {model.__name__}"
            )
        selected = [by_key[name] for name in fields]

    columns: t.List[str] = []
    for field in selected:
        if field.name in exclude or field.column in exclude:
            continue
        if field.column not in columns:
            columns.append(field.column)
    return columns


def _through_table(parent, nested: Nested) -> t.Optional[str]:
    """Resolve the through table for a many-to-many child, if any."""
    if isinstance(nested.through, str):
        return nested.through
    if nested.through is not None:  # a Django model
        return nested.through._meta.db_table
    for field in parent._meta.local_many_to_many:
        if field.remote_field.model is nested.model:
            return field.remote_field.through._meta.db_table
    return None


def _infer_relationship(parent, nested: Nested) -> dict:
    """Infer the PGSync relationship between parent and child models."""
    relationship: dict = {"variant": nested.variant}

    through = _through_table(parent, nested)
    if through is not None:
        relationship["type"] = nested.rel_type or ONE_TO_MANY
        relationship["through_tables"] = [through]
    else:
        rel_type = nested.rel_type
        if rel_type is None:
            # FK or OneToOne declared on the child, pointing at the parent
            for field in nested.model._meta.concrete_fields:
                if field.is_relation and field.related_model is parent:
                    rel_type = ONE_TO_ONE if field.one_to_one else ONE_TO_MANY
                    break
            else:
                # FK declared on the parent, pointing at the child
                # (e.g. Book.publisher): each parent row has one child row.
                for field in parent._meta.concrete_fields:
                    if field.is_relation and field.related_model is nested.model:
                        rel_type = ONE_TO_ONE
                        break
        if rel_type is None:
            raise SchemaGenerationError(
                f"Cannot infer relationship between "
                f"{parent.__name__} and {nested.model.__name__}: no foreign "
                f"key or many-to-many found. Pass type=/foreign_key= "
                f"explicitly."
            )
        relationship["type"] = rel_type

    if nested.foreign_key:
        relationship["foreign_key"] = nested.foreign_key
    return relationship


def build_child_node(parent, nested: Nested) -> dict:
    node: dict = {
        "table": nested.model._meta.db_table,
        "columns": model_columns(nested.model, nested.fields, nested.exclude),
        "relationship": _infer_relationship(parent, nested),
    }
    if nested.schema:
        node["schema"] = nested.schema
    if nested.label:
        node["label"] = nested.label
    if nested.transform:
        node["transform"] = nested.transform
    if nested.children:
        node["children"] = [
            build_child_node(nested.model, child) for child in nested.children
        ]
    return node


def build_nodes(index_cls: t.Type[PGSyncIndex]) -> dict:
    model = index_cls.model
    nodes: dict = {
        "table": model._meta.db_table,
        "columns": model_columns(model, index_cls.fields, index_cls.exclude),
    }
    if index_cls.schema_name:
        nodes["schema"] = index_cls.schema_name
    if index_cls.children:
        nodes["children"] = [
            build_child_node(model, child) for child in index_cls.children
        ]
    return nodes


def build_document(index_cls: t.Type[PGSyncIndex]) -> dict:
    """Build one PGSync schema document (one entry in schema.json)."""
    document: dict = {
        "database": index_cls.get_database_name(),
        "index": index_cls.get_index_name(),
        "nodes": build_nodes(index_cls),
    }
    if index_cls.plugins:
        document["plugins"] = list(index_cls.plugins)
    if index_cls.setting:
        document["setting"] = index_cls.setting
    if index_cls.mapping:
        document["mapping"] = index_cls.mapping
    if index_cls.routing:
        document["routing"] = index_cls.routing
    return document


def build_documents(
    index: t.Optional[str] = None,
) -> t.List[dict]:
    """Build schema documents for all registered indexes (or one by name)."""
    if index is not None:
        return [build_document(registry.get(index))]
    if not len(registry):
        raise SchemaGenerationError(
            "No PGSyncIndex classes registered. Define them in "
            "<app>/search_indexes.py and add 'django_pgsync' to "
            "INSTALLED_APPS."
        )
    return [build_document(index_cls) for index_cls in registry]
