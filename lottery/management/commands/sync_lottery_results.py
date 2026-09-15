from django.core.management.base import BaseCommand, CommandError

from lottery.services import DEFAULT_SYNC_LOOKBACK_DAYS, sync_results


class Command(BaseCommand):
    help = (
        "Sync Southern Vietnam lottery results from the GitHub fallback dataset into "
        "LotteryResult. Safe to re-run (idempotent) - meant to run once a day, e.g. via a "
        "PythonAnywhere Scheduled Task."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--lookback-days",
            type=int,
            default=DEFAULT_SYNC_LOOKBACK_DAYS,
            help="Only ingest results from this many days back (default: %(default)s).",
        )

    def handle(self, *args, **options):
        try:
            created = sync_results(lookback_days=options["lookback_days"])
        except Exception as exc:
            raise CommandError("Sync failed: {0}".format(exc))
        self.stdout.write(self.style.SUCCESS("Synced {0} new result(s).".format(created)))
