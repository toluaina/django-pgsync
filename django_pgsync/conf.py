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

#: Every environment setting pgsync 7.1.x reads (extracted from
#: pgsync/settings.py). Any of these can be set in the PGSYNC dict.
#: The system checks warn about keys not in this list (probable typos);
#: unknown keys are still exported, so newer pgsync settings keep working.
KNOWN_PGSYNC_SETTINGS = frozenset(
    {
        # general / performance
        "BLOCK_SIZE",
        "CHECKPOINT_PATH",
        "FILTER_CHUNK_SIZE",
        "JOIN_QUERIES",
        "LOGICAL_SLOT_CHUNK_SIZE",
        "NUM_WORKERS",
        "POLL_INTERVAL",
        "POLL_TIMEOUT",
        "POLLING",
        "QUERY_CHUNK_SIZE",
        "QUERY_LITERAL_BINDS",
        "STREAM_RESULTS",
        "USE_ASYNC",
        "WAL",
        # logging
        "CUSTOM_LOGGING",
        "FORMAT_WITH_COMMAS",
        "GENERAL_LOGGING_LEVEL",
        "LOG_HANDLERS",
        "LOG_INTERVAL",
        # schema sources
        "S3_SCHEMA_URL",
        "SCHEMA",
        "SCHEMA_URL",
        # search backend
        "ELASTICSEARCH",
        "ELASTICSEARCH_API_KEY",
        "ELASTICSEARCH_API_KEY_ID",
        "ELASTICSEARCH_AWS_HOSTED",
        "ELASTICSEARCH_AWS_REGION",
        "ELASTICSEARCH_BASIC_AUTH",
        "ELASTICSEARCH_BEARER_AUTH",
        "ELASTICSEARCH_CA_CERTS",
        "ELASTICSEARCH_CHUNK_SIZE",
        "ELASTICSEARCH_CLIENT_CERT",
        "ELASTICSEARCH_CLIENT_KEY",
        "ELASTICSEARCH_CLOUD_ID",
        "ELASTICSEARCH_HOST",
        "ELASTICSEARCH_HTTP_AUTH",
        "ELASTICSEARCH_MAX_BACKOFF",
        "ELASTICSEARCH_MAX_RETRIES",
        "ELASTICSEARCH_OPAQUE_ID",
        "ELASTICSEARCH_PASSWORD",
        "ELASTICSEARCH_POOL_MAXSIZE",
        "ELASTICSEARCH_PORT",
        "ELASTICSEARCH_QUEUE_SIZE",
        "ELASTICSEARCH_SCHEME",
        "ELASTICSEARCH_SSL_CONTEXT",
        "ELASTICSEARCH_SSL_VERSION",
        "ELASTICSEARCH_THREAD_COUNT",
        "ELASTICSEARCH_TIMEOUT",
        "ELASTICSEARCH_URL",
        "ELASTICSEARCH_USE_SSL",
        "ELASTICSEARCH_USER",
        "OPENSEARCH",
        "OPENSEARCH_AWS_HOSTED",
        # database
        "MYSQL_DATABASE",
        "PG_DATABASE",
        "PG_DRIVER",
        "PG_HOST",
        "PG_HOST_RO",
        "PG_PASSWORD",
        "PG_PASSWORD_RO",
        "PG_PORT",
        "PG_PORT_RO",
        "PG_SSLMODE",
        "PG_SSLMODE_RO",
        "PG_SSLROOTCERT",
        "PG_SSLROOTCERT_RO",
        "PG_URL",
        "PG_URL_RO",
        "PG_USER",
        "PG_USER_RO",
        "PG_WORK_MEM",
        "USE_UTF8MB4",
        # SQLAlchemy pool
        "SQLALCHEMY_MAX_OVERFLOW",
        "SQLALCHEMY_POOL_PRE_PING",
        "SQLALCHEMY_POOL_RECYCLE",
        "SQLALCHEMY_POOL_SIZE",
        "SQLALCHEMY_POOL_TIMEOUT",
        "SQLALCHEMY_USE_NULLPOOL",
        # redis
        "REDIS_AUTH",
        "REDIS_CHECKPOINT",
        "REDIS_DB",
        "REDIS_HOST",
        "REDIS_POLL_INTERVAL",
        "REDIS_PORT",
        "REDIS_READ_CHUNK_SIZE",
        "REDIS_RETRY_ON_TIMEOUT",
        "REDIS_SCHEME",
        "REDIS_SOCKET_TIMEOUT",
        "REDIS_URL",
        "REDIS_USER",
        "REDIS_WRITE_CHUNK_SIZE",
    }
)


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
