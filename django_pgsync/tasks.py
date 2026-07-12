"""Celery integration.

Schedule a periodic forward pass with Celery beat::

    # settings.py
    CELERY_BEAT_SCHEDULE = {
        "pgsync-pull": {
            "task": "django_pgsync.tasks.pgsync_pull",
            "schedule": 30.0,
        },
    }

Each run pulls everything committed since the last checkpoint and exits;
a run that dies resumes from the checkpoint on the next tick, so retries
are safe. A cache lock ensures only one pull per index runs at a time.

Note: PGSync's daemon/WAL streaming modes are long-running processes and
do not belong inside a Celery worker — use ``manage.py pgsync_daemon``
under systemd/supervisor for true streaming.
"""

import logging
import typing as t

try:
    from celery import shared_task
except ImportError as exc:  # pragma: no cover - exercised without celery
    raise ImportError(
        "django_pgsync.tasks requires Celery. Install it with: "
        'pip install "django-pgsync[celery]"'
    ) from exc

from django.core.cache import cache

logger = logging.getLogger(__name__)

#: Safety valve: the lock expires even if a worker is SIGKILLed mid-pull.
LOCK_TIMEOUT = 60 * 60


@shared_task(bind=True)
def pgsync_pull(
    self,
    index: t.Optional[str] = None,
    database_alias: str = "default",
):
    """Run one PGSync forward pass for one index, or all registered ones."""
    from .conf import export_pgsync_env, get_mode

    export_pgsync_env(database_alias)
    # In polling mode (the default) validation skips replication
    # slot/wal_level checks, so no superuser Postgres settings are needed.
    polling: bool = get_mode() == "polling"

    # Imported only now, after the environment is configured.
    from pgsync.sync import Sync

    from .schema import build_documents

    results: dict = {}
    for doc in build_documents(index):
        lock_key = f"django-pgsync:{doc['database']}:{doc['index']}"
        if not cache.add(lock_key, self.request.id or "lock", LOCK_TIMEOUT):
            logger.info("pgsync pull already running for %s", doc["index"])
            results[doc["index"]] = "skipped"
            continue
        try:
            sync = Sync(doc, polling=polling)
            sync.pull(polling=polling)
            results[doc["index"]] = "ok"
        finally:
            cache.delete(lock_key)
    return results
