'''
Created on Apr 15, 2013

@author: raybesiga
'''
import logging

from django.core.management.base import BaseCommand
from education.models import schedule_script_now
from optparse import OptionParser, make_option

logger = logging.getLogger(__name__)
logging.basicConfig(filename="script.log", level=logging.INFO)

handler = logging.handlers.RotatingFileHandler("script.log", maxBytes=5242880, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-d", "--date", dest="date"),
        make_option("-g", "--group", dest="group"),
        make_option("-s", "--slug", dest="slug"),
    )
    def handle(self, **options):
        if not options['group']:
            group = raw_input('Group--["Teachers", "Head Teachers", "SMC", "GEM"]: ')
        else:
            group = 'all'
        if not options['slug']:
            slug = raw_input('Script slug you wish to reschedule: ')
        else:
            slug = options['slug']

        schedule_script_now(grp=group, slug=slug)
        self.stdout.write('')
        self.stdout.write('done!')