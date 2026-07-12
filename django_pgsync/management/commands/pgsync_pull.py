from django_pgsync.management.base import PGSyncCommand
from django_pgsync.schema import build_documents


class Command(PGSyncCommand):
    help = (
        "Run a single PGSync forward pass: sync everything committed "
        "since the last checkpoint, then exit."
    )

    def handle(self, *args, **options):
        # In polling mode validation skips replication slot/wal_level
        # checks, so no superuser-level Postgres settings are required.
        polling: bool = self.configure(options) == "polling"
        from pgsync.sync import Sync

        for doc in build_documents(options["index"]):
            sync = Sync(doc, polling=polling)
            sync.pull(polling=polling)
            self.stdout.write(self.style.SUCCESS(f"Pulled: {doc['index']}"))
