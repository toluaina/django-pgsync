# Contributing to django-pgsync

Thanks for your interest in contributing! Issues, docs fixes and code are
all welcome.

## Getting set up

```bash
git clone https://github.com/toluaina/django-pgsync
cd django-pgsync
python -m venv .venv && source .venv/bin/activate
pip install django ruff pre-commit
pre-commit install        # lint + format run on every commit
```

## Running the tests

The suite is standalone — no database or search engine required:

```bash
python tests/runtests.py
```

Lint and formatting:

```bash
ruff check . && ruff format --check .
```

## Making changes

1. Open an issue first for anything non-trivial so we can agree on the
   approach before you invest time.
2. Fork, create a branch, make your change.
3. Add or update tests — schema-generation behavior in particular must be
   covered (see `tests/test_schema.py` and `tests/test_overrides.py`).
4. Update `CHANGELOG.md` under the `(unreleased)` section and the README
   if behavior changes.
5. Open a pull request. CI runs the test matrix (Python 3.10–3.14 ×
   Django 4.2–6.0) and lint; everything must be green.

## Guidelines

- Only new **runtime** dependencies with a strong justification — the
  package intentionally depends on just `django` and `pgsync`.
- Anything already released stays backwards compatible; deprecate before
  removing.
- Sync engine behavior belongs upstream in
  [pgsync](https://github.com/toluaina/pgsync) — this package is the
  Django integration layer (schema generation, commands, checks, Celery).
- End-to-end verification against a real PostgreSQL + Elasticsearch/
  OpenSearch is appreciated for runtime changes; the `example/` project
  is the quickest harness.

## Releasing

Maintainer-only — see [RELEASING.md](RELEASING.md).
