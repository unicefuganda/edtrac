from optparse import make_option
from django.core.management.base import BaseCommand
from education.models import send_report
from education.utils import _next_wednesday
import datetime

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (make_option('h', '--hour', dest='h'))
    def handle(self, **options):
        today_date = datetime.datetime.date(datetime.datetime.now())
        # send out reports on wednesday
        if _is_wednesday(today_date, hour=options['h']):
            send_report()
            self.stdout.write('done!')
