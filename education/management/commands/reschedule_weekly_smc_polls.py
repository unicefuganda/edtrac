'''
Created on Nov 1, 2011

@author: asseym
'''

from django.core.management.base import BaseCommand
from education.utils import reschedule_weekly_smc_polls

class Command(BaseCommand):
    def handle(self, **options):
        reschedule_weekly_smc_polls()
        self.stdout.write('done!')
