'''
Created on September 28, 2012

@author: raybesiga
'''

from django.core.management.base import BaseCommand
from django.conf import settings
from education.models import School, EmisReporter
import xlwt
from rapidsms.contrib.locations.models import Location
from rapidsms.models import Connection
from optparse import OptionParser, make_option
from poll.models import Poll


class Command(BaseCommand):
    """Generates Violence Reports By District"""
    
    def handle(self, **options):

        """Reporting Violence"""
        def violence_report():
            groups = Poll.objects.filter(name__endswith='_abuse')
            return groups
        
        book = xlwt.Workbook(encoding='utf-8')
        for poll in violence_report():
            sheet = book.add_sheet(poll.name, cell_overwrite_ok=True)
            rowx = 0
            colx = 0
            headings = ['District', 'Reporter', 'Message', 'Date']
            for colx, value in enumerate(headings):
                sheet.write(rowx, colx, value)
            sheet.set_panes_frozen(True)
            sheet.set_horz_split_pos(rowx+1)
            sheet.set_remove_splits(True)
            rowx = 1
                            
            for rep in poll.responses.all().values('contact__reporting_location__name', 'message__text', 'date', 'contact__name', 'poll__question'):
                sheet.write(rowx, 0, '%s' %rep['contact__reporting_location__name'])
                sheet.write(rowx, 1, '%s' % rep['contact__name'])
                sheet.write(rowx, 2, '%s' % rep['message__text'])
                sheet.write(rowx, 3, '%s' % rep['date'].strftime("%A, %B %d, %Y"))
                rowx +=1
                

        file_name = "violence_reports.xls"
        file_path = '%s%s' % (settings.SPREADSHEETS_PATH, file_name)
        book.save(file_path)  