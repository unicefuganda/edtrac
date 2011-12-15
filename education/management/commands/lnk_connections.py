'''
Created on Sep 15, 2011

@author: asseym
'''

from django.core.management.base import BaseCommand
from education.utils import match_connections

class Command(BaseCommand):
    def handle(self, **options):
        match_connections()
        self.stdout.write('done!')
