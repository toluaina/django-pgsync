"""Bridge Django settings to PGSync's environment-based configuration.

PGSync reads PG_* / ELASTICSEARCH_* / REDIS_* settings from the
environment at import time, so ``export_pgsync_env()`` must be called
BEFORE the first ``import pgsync``. The management commands and the
Celery task do this automatically.

Search/Redis endpoints and any other PGSync setting can be provided in
Django settings::

    PGSYNC = {
        "MODE": "polling",  # or "event" / "wal"; see MODES below
        "ELASTICSEARCH_URL": "https://search.internal:9200",
        "OPENSEARCH": True,
        "REDIS_HOST": "redis.internal",
        "CHECKPOINT_PATH": "/var/lib/pgsync",
    }

"MODE" configures django-pgsync itself; every other key is exported as a
PGSync environment setting.

Values already present in the process environment always win.
"""

import os
import typing as t

SUPPORTED_ENGINES = ("postgresql", "mysql")

#: polling: periodic pull; needs no wal_level=logical, replication slots,
#:          triggers or superuser — works on read-only/managed clusters.
#: event:   PGSync's default trigger + replication slot mode.
#: wal:     logical replication slot streaming, no triggers.
MODES = ("polling", "event", "wal")
DEFAULT_MODE = "polling"

#: Keys in the PGSYNC setting that configure django-pgsync itself and
#: must not be exported to the environment for pgsync.
RESERVED_KEYS = ("MODE",)


def get_mode() -> str:
    """Return the configured run mode.

    Defaults to "polling", the only mode that requires no superuser-level
    PostgreSQL settings (wal_level, replication slots, triggers).
    """
    from django.conf import settings

    mode = getattr(settings, "PGSYNC", {}).get("MODE", DEFAULT_MODE)
    if mode not in MODES:
        raise RuntimeError(f"Invalid PGSYNC['MODE'] {mode!r}; expected one of {MODES}")
    return mode


def mode_flags(mode: str) -> t.Dict[str, bool]:
    """Keyword flags to pass to pgsync.sync.Sync for a given mode."""
    return {"polling": mode == "polling", "wal": mode == "wal"}


def export_pgsync_env(database_alias: str = "default") -> None:
    from django.conf import settings

    db: dict = settings.DATABASES[database_alias]
    engine: str = db.get("ENGINE", "")
    if not any(name in engine for name in SUPPORTED_ENGINES):
        raise RuntimeError(
            f"django-pgsync requires a PostgreSQL or MySQL database; "
            f"got ENGINE={engine!r} for alias {database_alias!r}"
        )
    is_mysql: bool = "mysql" in engine

    # pgsync uses PG_* settings for all backends; PG_DRIVER selects
    # the MySQL driver.
    mapping: t.Dict[str, t.Any] = {
        "PG_HOST": db.get("HOST") or "localhost",
        "PG_PORT": db.get("PORT") or (3306 if is_mysql else 5432),
        "PG_USER": db.get("USER"),
        "PG_PASSWORD": db.get("PASSWORD"),
    }
    if is_mysql:
        mapping["PG_DRIVER"] = "pymysql"
    for key, value in mapping.items():
        if value not in (None, ""):
            os.environ.setdefault(key, str(value))

    for key, value in getattr(settings, "PGSYNC", {}).items():
        if key in RESERVED_KEYS:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        os.environ.setdefault(key, str(value))
