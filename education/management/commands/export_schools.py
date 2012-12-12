'''
Created on Dec 7, 2012

@author: raybesiga
'''

from django.core.management.base import BaseCommand
from django.conf import settings
from education.models import School, EmisReporter
import xlwt
from rapidsms.contrib.locations.models import Location
from rapidsms.models import Connection


class Command(BaseCommand):
    """Generates Schools Report By District"""
    
#    def reporting_districts(self):
    def handle(self, **options):
        
        """ Reporting Districts """
        def reporting_districts():
            locations = Location.objects.filter(name__in=EmisReporter.objects.values_list('reporting_location__name',flat=True).distinct())
            locs_list = []
            for loc in locations:
                if not Location.tree.root_nodes()[0].pk == loc.pk and loc.type.name == 'district':
                    locs_list.append(loc)
                    
            return locs_list
        
        book = xlwt.Workbook(encoding='utf-8')
        for district in reporting_districts():
            sheet = book.add_sheet(district.name, cell_overwrite_ok=True)
            rowx = 0
            colx = 0
            headings = ['School', 'District']
            for colx, value in enumerate(headings):
                sheet.write(rowx, colx, value)
            sheet.set_panes_frozen(True)
            sheet.set_horz_split_pos(rowx+1)
            sheet.set_remove_splits(True)
            rowx = 1

            for sch in School.objects.filter(pk__in=EmisReporter.objects.exclude(schools=None).\
                                        filter(reporting_location__name = district.name).distinct().values_list('schools__pk',flat=True)):
                sheet.write(rowx, 0, sch.name)
                sheet.write(rowx, 1, district.name)
#                sheet.write(rowx, 1, rep.name)
#                grps = ','.join(rep.groups.all().values_list('name', flat=True))
#                sheet.write(rowx, 2, grps)
#                connections = ','.join(Connection.objects.filter(contact=rep).values_list('identity', flat=True))
#                sheet.write(rowx, 3, connections)
#                names = ','.join(rep.schools.all().values_list('name', flat=True))
#                sheet.write(rowx, 4, names)
                rowx +=1
      
        file_name = "schools.xls"
        file_path = '%s%s' % (settings.SPREADSHEETS_PATH, file_name)
        book.save(file_path)