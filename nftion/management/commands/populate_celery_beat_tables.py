from django.core.management import BaseCommand, call_command
from ...celery_beat_utils import populate_intervals_and_periodic_tasks


class Command(BaseCommand):
    help = 'Runs migrations and populates intervals and periodic tasks'

    def handle(self, *args, **options):
        call_command('migrate')
        populate_intervals_and_periodic_tasks()
        self.stdout.write(self.style.SUCCESS('Successfully ran migrations and populated intervals and periodic tasks.'))
