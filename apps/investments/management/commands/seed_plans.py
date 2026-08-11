from django.core.management.base import BaseCommand

from apps.investments.models import InvestmentPlan
from apps.investments.seeding import seed


class Command(BaseCommand):
    help = 'Seed the holding plan catalog.'

    def handle(self, *args, **options):
        created, removed = seed()
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {InvestmentPlan.objects.count()} investment plans '
            f'({created} new, {removed} removed).'
        ))
