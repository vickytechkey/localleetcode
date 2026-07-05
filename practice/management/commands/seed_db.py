from django.core.management.base import BaseCommand
from practice.seed import run_seed

class Command(BaseCommand):
    help = 'Seeds the SQLite database with 200 DSA problems and their test cases'

    def handle(self, *args, **kwargs):
        self.stdout.write("Running database seed script...")
        run_seed()
        self.stdout.write(self.style.SUCCESS("Database seeding completed!"))
