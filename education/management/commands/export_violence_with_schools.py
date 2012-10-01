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
from poll.models import Poll


class Command(BaseCommand):
    """Generates Reports By District"""
    
#    def reporting_districts(self):
    def handle(self, **options):
        
        """ Reporting Districts """
        def violence_report():
            groups = Poll.objects.filter(name__endswith='_abuse')
            return groups
        
        book = xlwt.Workbook(encoding='utf-8')
        for poll in violence_report():
            sheet = book.add_sheet(poll.name, cell_overwrite_ok=True)
            rowx = 0
            colx = 0
            headings = ['District', 'Reporter Name', 'Reporter Message', 'Numbers', 'Schools']
            for colx, value in enumerate(headings):
                sheet.write(rowx, colx, value)
            sheet.set_panes_frozen(True)
            sheet.set_horz_split_pos(rowx+1)
            sheet.set_remove_splits(True)
            rowx = 1
            
            def reporting_districts():
                locations = Location.objects.filter(name__in=EmisReporter.objects.values('reporting_location__name',flat=True).distinct())
                districts = []
                for loc in locations:
                    if not Location.tree.root_nodes()[0].pk == loc.pk and loc.type.name == 'district':
                        districts.append(loc)
                return districts
                
            for rep in EmisReporter.objects.filter(polls__name__in=Poll.objects.filter(name__endswith='_abuse').values()):
#                data = [district.name, rep.schools.all(), rep.name, Connection.objects.filter(contact=rep)]
                for district in reporting_districts():
                    sheet.write(rowx, 0, district.name)
                    sheet.write(rowx, 1, rep.name)
                    message = rep.message.all().values_list('text')
#                    grps = ','.join(rep.groups.all().values_list('name', flat=True))
                    sheet.write(rowx, 2, message)
                    connections = ','.join(Connection.objects.filter(contact=rep).values_list('identity', flat=True))
                    sheet.write(rowx, 3, connections)
                    names = ','.join(rep.schools.all().values_list('name', flat=True))
                    sheet.write(rowx, 4, names)
                    rowx +=1
      
        file_name = "violence_report_by_group.xls"
        file_path = '%s%s' % (settings.SPREADSHEETS_PATH, file_name)
        book.save(file_path)