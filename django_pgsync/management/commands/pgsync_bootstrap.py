from django_pgsync.conf import mode_flags
from django_pgsync.management.base import PGSyncCommand
from django_pgsync.schema import build_documents


class Command(PGSyncCommand):
    help = (
        "One-time PGSync setup: search indices, plus triggers/replication "
        "slots when the mode needs them (polling mode needs neither). "
        "Idempotent; rerun after schema changes. PostgreSQL only — MySQL/"
        "MariaDB pipelines need no bootstrap and run in polling mode."
    )

    def add_pgsync_arguments(self, parser):
        parser.add_argument(
            "--teardown",
            action="store_true",
            help="Remove triggers and replication slots instead",
        )

    def handle(self, *args, **options):
        mode: str = self.configure(options)
        flags: dict = mode_flags(mode)
        from pgsync.sync import Sync

        teardown: bool = options["teardown"]
        for doc in build_documents(options["index"]):
            sync = Sync(
                doc,
                validate=not teardown,
                repl_slots=False,
                polling=flags["polling"],
            )
            if teardown:
                sync.teardown(**flags)
                self.stdout.write(self.style.WARNING(f"Teardown: {doc['index']}"))
            else:
                sync.setup(**flags)
                self.stdout.write(
                    self.style.SUCCESS(f"Bootstrap ({mode}): {doc['index']}")
                )
