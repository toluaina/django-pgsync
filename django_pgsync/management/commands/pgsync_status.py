from django_pgsync.indexes import registry
from django_pgsync.management.base import PGSyncCommand


class Command(PGSyncCommand):
    help = (
        "Show sync status per index: database row count vs search index document count."
    )

    def handle(self, *args, **options):
        self.configure(options)
        from pgsync.search_client import SearchClient

        client = SearchClient()
        index_classes = (
            [registry.get(options["index"])] if options["index"] else registry.all()
        )
        drift = False
        for index_cls in index_classes:
            name = index_cls.get_index_name()
            rows = index_cls.model._default_manager.using(
                index_cls.database_alias
            ).count()
            try:
                docs = client.search(
                    name,
                    {
                        "query": {"match_all": {}},
                        "size": 0,
                        "track_total_hits": True,
                    },
                )["hits"]["total"]["value"]
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"{name}: {rows} rows, index unavailable ({exc})")
                )
                drift = True
                continue

            line = f"{name}: {rows} rows, {docs} documents"
            if docs == rows:
                self.stdout.write(self.style.SUCCESS(f"{line} — in sync"))
            else:
                # The search doc count can lag briefly until a refresh, and
                # root-row deletes never propagate in polling mode.
                self.stdout.write(
                    self.style.WARNING(f"{line} — drift of {docs - rows:+d}")
                )
                drift = True
        if drift:
            raise SystemExit(1)
