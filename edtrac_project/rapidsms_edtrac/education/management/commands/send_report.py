from optparse import make_option
from django.core.management.base import BaseCommand
from education.models import send_report
from education.utils import _is_wednesday

class Command(BaseCommand):
    def handle(self, **options):
        # send out reports on wednesday
        if _is_wednesday()[1]:
            print "is wednesday"
            send_report()
            self.stdout.write('done!')
        else:
            print "not wednesday"
