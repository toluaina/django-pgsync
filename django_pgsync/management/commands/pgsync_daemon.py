import asyncio
import threading
import time

from django_pgsync.management.base import PGSyncCommand
from django_pgsync.schema import build_documents


class Command(PGSyncCommand):
    help = (
        "Run PGSync continuously. Long-running: run under "
        "systemd/supervisor, not inside a Celery worker. Modes: "
        "polling (default; no superuser Postgres settings required), "
        "event (triggers + replication slot), wal (slot streaming)."
    )

    def handle(self, *args, **options):
        mode: str = self.configure(options)
        self.stdout.write(f"Starting PGSync in {mode!r} mode")

        from pgsync import settings as pgsync_settings
        from pgsync.sync import Sync

        if mode == "polling":
            try:
                while True:
                    for doc in build_documents(options["index"]):
                        sync = Sync(doc, polling=True)
                        sync.pull(polling=True)
                    time.sleep(pgsync_settings.POLL_INTERVAL)
            except KeyboardInterrupt:
                self.stdout.write("Stopped.")

        elif mode == "wal":
            syncs = [Sync(doc, wal=True) for doc in build_documents(options["index"])]
            # Extra schema entries run in daemon threads; the first runs
            # on the main thread so KeyboardInterrupt works naturally.
            for sync in syncs[1:]:
                threading.Thread(target=sync.wal_consumer, daemon=True).start()
            if syncs:
                syncs[0].wal_consumer()

        else:  # event
            tasks = []
            for doc in build_documents(options["index"]):
                sync = Sync(doc)
                sync.pull()
                sync.receive()
                tasks.extend(sync.tasks)
            if pgsync_settings.USE_ASYNC and tasks:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(asyncio.gather(*tasks))
                loop.close()
