# Changelog

## 0.1.0 (unreleased)

Initial release.

- `PGSyncIndex`/`Nested` declarative API with `search_indexes.py`
  autodiscovery across installed apps.
- PGSync schema generation from Django model metadata, with automatic
  relationship inference: foreign keys, reverse foreign keys, one-to-one
  fields, and many-to-many through tables.
- Management commands: `pgsync_schema`, `pgsync_bootstrap`, `pgsync_pull`,
  `pgsync_daemon`.
- Optional Celery beat task (`django_pgsync.tasks.pgsync_pull`) for
  polling-mode sync with cache-based overlap locking.
- Database credentials bridged automatically from Django `DATABASES`;
  additional PGSync settings via the `PGSYNC` Django setting.
- Run mode selection via `PGSYNC["MODE"]` or `--mode`: `polling`
  (default — requires no superuser Postgres settings, no replication
  slots or triggers), `event` (triggers + slot), `wal` (slot streaming).
- Django system checks validating the `PGSYNC` setting at startup
  (`django_pgsync.E001`, `E002`, `W001`).
- MySQL/MariaDB database aliases export `PG_DRIVER=pymysql` and default
  to port 3306 (polling mode only; PGSync bootstrap is PostgreSQL-specific).
- Importing `django_pgsync.tasks` without Celery raises an actionable
  error pointing at the `django-pgsync[celery]` extra.
- Catalogue of all 90+ PGSync environment settings
  (`django_pgsync.conf.KNOWN_PGSYNC_SETTINGS`); the system checks warn
  about unrecognized `PGSYNC` keys so typos surface at startup
  (`django_pgsync.W002`).
- Startup schema validation: every registered index must generate a
  valid schema or `manage.py check` fails (`django_pgsync.E003`).
- `pgsync_status` command comparing database row counts with search
  index document counts; exits non-zero on drift (usable in monitoring).
- Pre-commit configuration (ruff lint + format, whitespace/YAML/TOML
  checks).
