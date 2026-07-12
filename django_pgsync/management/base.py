from django.core.management.base import BaseCommand

from django_pgsync.conf import MODES, export_pgsync_env, get_mode


class PGSyncCommand(BaseCommand):
    """Base for pgsync_* commands: shared arguments and env setup."""

    #: Commands that connect to the database also take --database/--mode.
    requires_connection = True

    def add_arguments(self, parser):
        parser.add_argument("--index", help="Only this index")
        if self.requires_connection:
            parser.add_argument("--database", default="default", help="Django DB alias")
            parser.add_argument(
                "--mode",
                choices=MODES,
                help="Override PGSYNC['MODE'] (default: polling)",
            )
        self.add_pgsync_arguments(parser)

    def add_pgsync_arguments(self, parser):
        """Hook for subclasses to add their own arguments."""

    def configure(self, options) -> str:
        """Export PGSync env from Django settings; return the run mode."""
        export_pgsync_env(options["database"])
        return options["mode"] or get_mode()
