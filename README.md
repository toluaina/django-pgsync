# django-pgsync

**Real-time Elasticsearch/OpenSearch indexing for Django — powered by
[PGSync](https://github.com/toluaina/pgsync) change data capture.**

[![PyPI](https://img.shields.io/pypi/v/django-pgsync)](https://pypi.org/project/django-pgsync/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-pgsync)](https://pypi.org/project/django-pgsync/)
[![Django versions](https://img.shields.io/pypi/frameworkversions/django/django-pgsync)](https://pypi.org/project/django-pgsync/)
[![Tests](https://github.com/toluaina/django-pgsync/actions/workflows/test.yml/badge.svg)](https://github.com/toluaina/django-pgsync/actions/workflows/test.yml)
[![License](https://img.shields.io/pypi/l/django-pgsync)](https://github.com/toluaina/django-pgsync/blob/main/LICENSE)

Declare search indexes from your Django models — nested documents,
relationships and all — and let PGSync keep them in sync with your
database. No signals, no `save()` overrides, no missed writes.

```python
# <app>/search_indexes.py
from django_pgsync import PGSyncIndex, Nested
from .models import Author, Book, Publisher, Rating

class BookIndex(PGSyncIndex):
    model = Book
    index = "books"
    fields = ["isbn", "title", "description"]
    children = [
        Nested(Rating),                      # FK on Rating   -> one_to_many
        Nested(Publisher, fields=["name"]),  # FK on Book     -> one_to_one
        Nested(Author),                      # M2M            -> through table
    ]
```

## Why not signals?

Signal-based indexers (django-elasticsearch-dsl, Haystack) hook into the
ORM, so anything that bypasses `Model.save()` silently never reaches your
index. PGSync watches the **database** instead:

| Write path                        | Signal-based indexers | django-pgsync |
|-----------------------------------|:---------------------:|:-------------:|
| `instance.save()` / `delete()`    | ✅                    | ✅            |
| `queryset.update()` / `delete()`  | ❌                    | ✅            |
| `bulk_create()` / `bulk_update()` | ❌                    | ✅            |
| Cascade deletes                   | ❌                    | ✅            |
| Raw SQL / data migrations         | ❌                    | ✅            |
| Writes from other services        | ❌                    | ✅            |

You also get PGSync's engine for free: automatic denormalization into
nested documents, initial bootstrap, checkpointing and crash recovery.

## Installation

```bash
pip install django-pgsync            # includes pgsync
pip install "django-pgsync[celery]"  # with Celery beat support
```

Requires Python 3.10+, Django 4.2+, PostgreSQL, and Elasticsearch or
OpenSearch. MySQL/MariaDB works in `polling` mode only (PGSync's
bootstrap is PostgreSQL-specific; skip `pgsync_bootstrap`).

## Quick start

**1. Register the app**

```python
INSTALLED_APPS = [
    ...,
    "django_pgsync",
]

# Optional: PGSync settings not derivable from DATABASES
PGSYNC = {
    "MODE": "polling",  # "polling" (default) | "event" | "wal"
    "ELASTICSEARCH_URL": "http://localhost:9200",
    "REDIS_HOST": "localhost",
}
```

Database credentials are taken from `DATABASES["default"]` automatically.
Environment variables already set (e.g. `PG_PASSWORD`) always take precedence.
`MODE` configures django-pgsync itself; every other key is passed through to
PGSync as an environment setting.

**2. Declare an index** in `<app>/search_indexes.py` (see the example
above). Relationships are inferred from model metadata: foreign keys,
one-to-one fields, and many-to-many through tables. Override with
`Nested(..., type="one_to_many", through=..., foreign_key={...})` when
needed.

**3. Bootstrap and run**

```bash
python manage.py pgsync_schema              # inspect generated schema JSON
python manage.py pgsync_bootstrap           # one-time setup for the mode
python manage.py pgsync_pull                # one-shot sync, then exit
python manage.py pgsync_daemon              # continuous sync (systemd etc.)
```

## Run modes

| Mode | How it works | Postgres requirements |
|---|---|---|
| `polling` (default) | Periodic forward pass every `POLL_INTERVAL` seconds | **None beyond read access** — no `wal_level=logical`, replication slots, triggers or superuser; works on read-only and managed clusters |
| `event` | Database triggers + `pg_notify` + replication slot | `wal_level=logical`, replication slot rights, trigger installation |
| `wal` | Streams the logical replication slot directly, no triggers | `wal_level=logical`, replication slot rights |

`polling` is the default precisely because it needs no superuser-level
database settings — ideal for hosted Postgres (RDS, Cloud SQL, Supabase)
where you may not control `wal_level`. Two trade-offs: sync latency is the
poll interval rather than milliseconds, and **deleting a root row leaves a
stale document in the index** (there is no delete record to observe;
child-row deletes are fine since the parent document is rebuilt). If you
hard-delete root rows, use `wal`/`event` mode or a soft-delete flag. When
you control the database, `wal` gives the lowest overhead real-time sync:

```python
PGSYNC = {"MODE": "wal", ...}
```

All commands also accept `--mode` to override the setting per invocation.
`pgsync_bootstrap` does the right thing per mode: in `polling` it skips
triggers and replication slots entirely; in `wal` it creates only the slot;
in `event` it creates both.

## Celery beat (polling mode)

For near-real-time sync without a dedicated daemon process, schedule a
periodic forward pass:

```python
CELERY_BEAT_SCHEDULE = {
    "pgsync-pull": {
        "task": "django_pgsync.tasks.pgsync_pull",
        "schedule": 30.0,
    },
}
```

Each run syncs everything committed since the last checkpoint and exits.
A cache lock prevents overlapping runs; interrupted runs resume from the
checkpoint. Do **not** run `pgsync_daemon` inside a Celery worker — a task
that never returns permanently occupies a worker slot.

## Management commands

| Command | Purpose |
|---|---|
| `pgsync_schema [--write PATH]` | Print or write the generated PGSync schema JSON |
| `pgsync_bootstrap [--teardown]` | One-time setup (or removal) of triggers, replication slots and indices |
| `pgsync_pull` | Single forward pass from the last checkpoint |
| `pgsync_daemon` | Continuous sync (long-running) |

All commands accept `--index <name>`, `--database <alias>` and `--mode`.

## Status

Alpha. Schema generation is fully tested; runtime commands wrap the
standard PGSync entry points.

## Example project

A complete runnable demo — models, index, seed data, sync, and the CDC
proof — lives in [`example/`](https://github.com/toluaina/django-pgsync/tree/main/example):

```bash
cd example
createdb django_pgsync_demo
python manage.py migrate --run-syncdb && python manage.py seed_bookstore
python manage.py pgsync_bootstrap && python manage.py pgsync_pull
curl -s "localhost:9200/demo-books/_search?q=sandworms"
```

## Links

- [PGSync documentation](https://pgsync.com)
- [PGSync on GitHub](https://github.com/toluaina/pgsync)
- [Changelog](https://github.com/toluaina/django-pgsync/blob/main/CHANGELOG.md)
- [Issue tracker](https://github.com/toluaina/django-pgsync/issues)

## Development

```bash
pip install django ruff
python tests/runtests.py
ruff check . && ruff format --check .
```

## License

MIT — see [LICENSE](https://github.com/toluaina/django-pgsync/blob/main/LICENSE).
