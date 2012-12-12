'''
Created on November 21, 2012

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
    """Generates Absenteeism Reports by Poll"""
    
    def handle(self, **options):

        """Reporting Absenteeism"""
        def wash_polls():
            toret = Poll.objects.filter(name__in=['edtrac_boysp3_attendance', \
                                                  'edtrac_girlsp3_attendance', \
                                                  'edtrac_boysp6_attendance', \
                                                  'edtrac_girlsp6_attendance', \
                                                  'edtrac_f_teachers_attendance', \
                                                  'edtrac_m_teachers_attendance', \
                                                  'edtrac_head_teachers_attendance'])
            return toret
        
        book = xlwt.Workbook(encoding='utf-8')
        for poll in wash_polls():
            sheet = book.add_sheet(poll.name, cell_overwrite_ok=True)
            rowx = 0
            colx = 0
            headings = ['Reporter', 'Phone Numbers', 'Schools', 'District', 'Message', 'Date']
            for colx, value in enumerate(headings):
                sheet.write(rowx, colx, value)
            sheet.set_panes_frozen(True)
            sheet.set_horz_split_pos(rowx+1)
            sheet.set_remove_splits(True)
            rowx = 1
                
            for resp in poll.responses.all():
                sheet.write(rowx, 0, '%s' % resp.contact.emisreporter.name)
                pnumbers = ','.join(resp.contact.emisreporter.connection_set.all().values_list('identity', flat=True))
                sheet.write(rowx, 1, '%s' % pnumbers)
                schools = ','.join(resp.contact.emisreporter.schools.all().values_list('name', flat=True))
                sheet.write(rowx, 2, '%s' % schools)
                sheet.write(rowx, 3, '%s' % resp.contact.emisreporter.reporting_location.name)
                sheet.write(rowx, 4, '%s' % resp.message.text)
                sheet.write(rowx, 5, '%s' % resp.date.strftime("%d %B, %Y"))
                rowx +=1
                

        file_name = "absenteeism_report.xls"
        file_path = '%s%s' % (settings.SPREADSHEETS_PATH, file_name)
        book.save(file_path)  