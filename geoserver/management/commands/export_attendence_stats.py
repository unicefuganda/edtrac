from django.db.utils import DatabaseError
from uganda_common.utils import total_submissions, reorganize_location, total_attribute_value, previous_calendar_week, previous_calendar_month
from education.reports import location_values,GRADES
from django.core.management.base import BaseCommand
import urllib2
from geoserver.models import EmisAttendenceData
from poll.models import Poll
from rapidsms.contrib.locations.models import Location
from django.conf import settings

def attendance_stats(district):
    stats = []
    location = Location.tree.root_nodes()[0]
    start_date, end_date = previous_calendar_week()
    dates = {'start':start_date, 'end':end_date}
#    import pdb;pdb.set_trace()
    boys = ["boys_%s" % g for g in GRADES]
    values = total_attribute_value(boys, start_date=start_date, end_date=end_date, location=location)
    stats.append(('boys', location_values(district, values)))

    girls = ["girls_%s" % g for g in GRADES]
    values = total_attribute_value(girls, start_date=start_date, end_date=end_date, location=location)
    stats.append(('girls', location_values(district, values)))

    total_pupils = ["boys_%s" % g for g in GRADES] + ["girls_%s" % g for g in GRADES]
    values = total_attribute_value(total_pupils, start_date=start_date, end_date=end_date, location=location)
    stats.append(('total pupils', location_values(district, values)))

    values = total_attribute_value("teachers_f", start_date=start_date, end_date=end_date, location=location)
    stats.append(('female teachers', location_values(district, values)))

    values = total_attribute_value("teachers_m", start_date=start_date, end_date=end_date, location=location)
    stats.append(('male teachers', location_values(district, values)))

    values = total_attribute_value(["teachers_f", "teachers_m"], start_date=start_date, end_date=end_date, location=location)
    stats.append(('total teachers', location_values(district, values)))
    res = {}
    res['dates'] = dates
    res['stats'] = stats
    return res

class Command(BaseCommand):
    
    help = """loads weekly attendence statistics to  geoserver"""

    def handle(self, **options):
        uganda=Location.objects.get(name="Kotido")
        districts=Location.objects.filter(type="district")
        for district in districts:
            district_data,created = EmisAttendenceData.objects.using('geoserver').get_or_create(district=district.name)
            try:
                stats=attendance_stats(district)
                print stats
            except (DatabaseError,IndexError):
                continue

            if len(stats.get('stats',None)):
                district_data.start_date=stats['dates'].get('start',None)
                district_data.end_date=stats['dates'].get('end',None)

                if not dict(stats['stats']).get("total pupils",0) == '-' and not dict(stats['stats']).get("total teachers",0) == '-':
                    district_data.boys=dict(stats['stats']).get("boys",0)
                    district_data.girls=dict(stats['stats']).get("girls",0)
                    district_data.total_pupils=dict(stats['stats']).get("total pupils",0)
                    district_data.female_teachers=dict(stats['stats']).get("female teachers",0)
                    district_data.male_teachers=dict(stats['stats']).get("male teachers",0)
                    district_data.total_teachers=dict(stats['stats']).get("total teachers",0)
                else:
                    district_data.boys=0
                    district_data.girls=0
                    district_data.total_pupils=0
                    district_data.female_teachers=0
                    district_data.male_teachers=0
                    district_data.total_teachers=0
                district_data.save()
            else:
                continue

