import datetime
from django.core.management.base import BaseCommand
from optparse import make_option
from education.scheduling import schedule_script_at
from script.models import Script

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-s", "--slug", dest="slug"),
    )

    def handle(self, **options):
        if not options['slug']:
            slug = raw_input('Script slug you wish to reschedule now: ')
        else:
            slug = options['slug']

        script = Script.objects.get(slug=slug)
        schedule_script_at(script, datetime.datetime.now())
        self.stdout.write('Done!\n')
