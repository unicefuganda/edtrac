from django.core.management import BaseCommand
from rapidsms.models import Connection

__author__ = 'kenneth'


class Command(BaseCommand):
    def handle(self, *args, **options):
        for a in Connection.objects.all():
            try:
                ls = a.messages.filter(direction='I').latest('date')
                r = a.contact.emisreporter
                r.last_reporting_date = ls.date
                r.save()
                print r, 'update last reporting date to', r.last_reporting_date
            except Exception as e:
                print 'not updated', e
