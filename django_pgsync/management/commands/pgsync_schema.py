import json

from django_pgsync.management.base import PGSyncCommand
from django_pgsync.schema import build_documents


class Command(PGSyncCommand):
    help = "Print (or write) the PGSync schema generated from PGSyncIndex definitions."

    # Schema generation reads model metadata only; no database connection.
    requires_connection = False

    def add_pgsync_arguments(self, parser):
        parser.add_argument("--write", metavar="PATH", help="Write schema JSON to PATH")

    def handle(self, *args, **options):
        payload = json.dumps(build_documents(options["index"]), indent=2)
        if options["write"]:
            with open(options["write"], "w") as fp:
                fp.write(payload + "\n")
            self.stdout.write(self.style.SUCCESS(f"Wrote {options['write']}"))
        else:
            self.stdout.write(payload)
