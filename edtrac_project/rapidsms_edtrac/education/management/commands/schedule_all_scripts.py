from django.core.management.base import BaseCommand
from education.scheduling import schedule_script
from script.models import Script

class Command(BaseCommand):

    def handle(self, **options):
        for script in Script.objects.all():
            schedule_script(script)
        self.stdout.write('Done!\n')
