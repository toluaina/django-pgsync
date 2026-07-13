# django-pgsync example: bookstore

A minimal Django project showing django-pgsync end to end: three related
models, a declarative search index, and real sync into Elasticsearch or
OpenSearch.

## Prerequisites

- PostgreSQL running locally (any user that can create a database)
- Elasticsearch or OpenSearch on `http://localhost:9200`
- django-pgsync installed: `pip install django-pgsync`

## Run it

```bash
cd example

# 1. Create the database and tables
createdb django_pgsync_demo
python manage.py migrate --run-syncdb

# 2. Seed demo data
python manage.py seed_bookstore

# 3. Using OpenSearch? Tell pgsync:
export OPENSEARCH=true

# 4. Inspect the generated PGSync schema (optional)
python manage.py pgsync_schema

# 5. One-time setup, then sync
python manage.py pgsync_bootstrap
python manage.py pgsync_pull

# 6. See the nested documents
curl -s "localhost:9200/demo-books/_search?q=sandworms" | python -m json.tool
```

Then prove the CDC claim — make a change no signal-based indexer would see:

```bash
python manage.py shell -c "
from bookstore.models import Book
Book.objects.filter(isbn='9780441172719').update(title='Dune (Deluxe Edition)')
"
python manage.py pgsync_pull
curl -s "localhost:9200/demo-books/_doc/9780441172719" | python -m json.tool
```

## Continuous sync

Either run the daemon:

```bash
python manage.py pgsync_daemon        # polling loop; Ctrl+C to stop
```

or schedule `django_pgsync.tasks.pgsync_pull` with Celery beat — see the
main README.

## Cleanup

```bash
curl -s -X DELETE localhost:9200/demo-books
dropdb django_pgsync_demo
```

Environment overrides for the database and search endpoints are listed at
the top of `project/settings.py`.
