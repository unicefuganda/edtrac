'''
Created on Nov 1, 2011

@author: asseym
'''

from django.core.management.base import BaseCommand
from education.models import reschedule_monthly_polls

class Command(BaseCommand):
    def handle(self, **options):
        reschedule_monthly_polls()
        self.stdout.write('done!')
