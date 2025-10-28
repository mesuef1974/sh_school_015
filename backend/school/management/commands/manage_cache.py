"""
Management command to manage application cache
Usage:
  python manage.py manage_cache --clear
  python manage.py manage_cache --warm
  python manage.py manage_cache --stats
"""

from django.core.cache import caches
from django.core.management.base import BaseCommand
from school.cache_utils import clear_all_caches, warm_cache


class Command(BaseCommand):
    help = "Manage application cache (clear, warm up, show stats)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear all caches")
        parser.add_argument(
            "--clear-cache",
            type=str,
            help="Clear specific cache (default, long_term, attendance)",
        )
        parser.add_argument(
            "--warm",
            action="store_true",
            help="Warm up cache with frequently accessed data",
        )
        parser.add_argument("--stats", action="store_true", help="Show cache statistics")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing all caches..."))
            clear_all_caches()
            self.stdout.write(self.style.SUCCESS("✓ All caches cleared"))

        elif options["clear_cache"]:
            cache_name = options["clear_cache"]
            if cache_name not in ["default", "long_term", "attendance"]:
                self.stdout.write(self.style.ERROR(f"Invalid cache name: {cache_name}"))
                return

            self.stdout.write(self.style.WARNING(f"Clearing {cache_name} cache..."))
            caches[cache_name].clear()
            self.stdout.write(self.style.SUCCESS(f'✓ Cache "{cache_name}" cleared'))

        elif options["warm"]:
            self.stdout.write(self.style.WARNING("Warming up cache..."))
            warm_cache()
            self.stdout.write(self.style.SUCCESS("✓ Cache warmed up successfully"))

        elif options["stats"]:
            self.show_cache_stats()

        else:
            self.stdout.write(self.style.ERROR("Please specify an action: --clear, --warm, or --stats"))

    def show_cache_stats(self):
        """Display cache statistics"""
        self.stdout.write(self.style.SUCCESS("\nCache Statistics:"))
        self.stdout.write("=" * 60)

        for cache_name in ["default", "long_term", "attendance"]:
            cache_backend = caches[cache_name]
            self.stdout.write(f"\n{cache_name.upper()} Cache:")

            try:
                # Try to get stats (Redis specific)
                client = cache_backend._cache.get_client()
                info = client.info("stats")

                self.stdout.write(f'  Total connections: {info.get("total_connections_received", "N/A")}')
                self.stdout.write(f'  Total commands: {info.get("total_commands_processed", "N/A")}')
                self.stdout.write(f'  Keyspace hits: {info.get("keyspace_hits", "N/A")}')
                self.stdout.write(f'  Keyspace misses: {info.get("keyspace_misses", "N/A")}')

                hits = int(info.get("keyspace_hits", 0))
                misses = int(info.get("keyspace_misses", 0))
                total = hits + misses
                if total > 0:
                    hit_rate = (hits / total) * 100
                    self.stdout.write(self.style.SUCCESS(f"  Hit rate: {hit_rate:.2f}%"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Could not retrieve stats: {e}"))

        self.stdout.write("\n" + "=" * 60)
