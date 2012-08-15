from django.core.management.base import BaseCommand
from education.models import EnrolledDeployedQuestionsAnswered, EmisReporter,School
from poll.models import Poll, ResponseCategory
import xlwt, dateutils, datetime
from django.conf import settings
from education.reports import get_day_range
class Command(BaseCommand):

    def handle(self, *args, **options):
    # ideally head teachers match the number of SMCs in eductrac
        book = xlwt.Workbook()
        school_dates = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
        first_date = school_dates[0]
        last_date = school_dates[1]
        date_bunches = []
        while first_date <= last_date:
            tmp = get_day_range(first_date)
            first_date  = tmp[0]
            date_bunches.append(get_day_range(first_date))
            first_date = dateutils.increment(first_date, weeks = 1)

        headings = ['School'] + [d.strftime("%d/%m/%Y") for d, _ in date_bunches]
        head_teacher_poll = Poll.objects.select_related().get(name = 'edtrac_head_teachers_attendance')
        enrolled_answered = EnrolledDeployedQuestionsAnswered.objects.select_related()
        district_names = enrolled_answered.values_list('school__location__name',flat=True).distinct()

        district_schools = {}
        for dn in district_names:
            district_schools[dn] = School.objects.select_related().filter(pk__in =\
                enrolled_answered.filter(school__location__name = dn).values_list('school__pk',flat=True)).order_by('name')


#TODO >>> split the head teachers in 2
#        female_head_teachers = EmisReporter.objects.filter(reporting_location__in =\
#            locations, groups__name="Head Teachers", gender='F').exclude(schools = None)
#
#        male_head_teachers = EmisReporter.objects.filter(reporting_location__in =\
#            locations, groups__name="Head Teachers", gender='M').exclude(schools = None)


        for district_name in district_schools.keys():
            print district_name
            container = []

            sheet = book.add_sheet(district_name, cell_overwrite_ok=True)
            rowx = 0
            for colx, val_headings in enumerate(headings):
                sheet.write(rowx, colx, val_headings)
                sheet.set_panes_frozen(True)
                sheet.set_horz_split_pos(rowx+1) # in general, freeze after last heading row
                sheet.set_remove_splits(True) # if user does unfreeze, don't leave a split there


            for school in district_schools[district_name]:
                school_vals = [school.name]
                for d_bunch in date_bunches:
                    submission_count = 0
                    yes_count = ResponseCategory.objects.filter(category__name = 'yes',
                        response__in=head_teacher_poll.responses.filter(date__range = d_bunch,
                        contact__emisreporter__schools = school)).count()
                    school_vals.extend([yes_count])

                container.append(school_vals)

            for row in container:
                rowx += 1
                for colx, value in enumerate(row):
                    sheet.write(rowx, colx, value)
        book.save('HeadTeacherReport.xls')