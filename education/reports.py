from __future__ import division
from exceptions import ZeroDivisionError
from django.conf import settings
from django.core.serializers import serialize
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from generic.reports import Report
from generic.reporting.reports import Column
from generic.utils import flatten_list
from rapidsms.contrib.locations.models import Location
from rapidsms_httprouter.models import Message
from rapidsms.models import Connection
from django.db.models import Q, Sum, StdDev, Max, Min, Avg, Count
from script.models import Script
from rapidsms_xforms.models import XFormSubmissionValue, XForm, XFormSubmission
from uganda_common.reports import PollNumericResultsColumn
from uganda_common.utils import total_submissions, reorganize_location
from uganda_common.utils import reorganize_dictionary
from education.utils import previous_calendar_week, Statistics
from education.models import EmisReporter, School
from poll.models import Response, Poll
import datetime
from dateutil.relativedelta import relativedelta
from eav.models import Value, ContentType
from rapidsms.models import Contact
from unregister.models import Blacklist
import exceptions
import xlwt
from dateutil.parser import parse
import commands
import dateutils
import operator

GRADES = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']
polls = Poll.objects.all()
locations = Location.objects.all()
all_schools = School.objects.all()


def get_location_for_user(user):
    return user.get_profile().location


def get_location(request):
    #location of current logged in user or selected district
    district_id = request.POST.get('district_id') or request.GET.get('district_id')
    user_location = locations.get(pk=district_id) if district_id else get_location_for_user(request.user)
    return user_location


def attrib_ratios(top_attrib, bottom_attrib, dates, location):

    top_value = XFormSubmissionValue.objects.exclude(submission__has_errors=True)\
        .exclude(submission__connection__contact=None)\
        .filter(created__range=(dates.get('start'), dates.get('end')))\
        .filter(attribute__slug__in=top_attrib)\
        .filter(submission__connection__contact__emisreporter__schools__location__in=location.get_descendants(include_self=True).all())\
        .annotate(Sum('value_int')).values_list('value_int__sum', flat=True)

    bottom_value = XFormSubmissionValue.objects.exclude(submission__has_errors=True)\
        .exclude(submission__connection__contact=None)\
        .filter(created__range=(dates.get('start'), dates.get('end')))\
        .filter(attribute__slug__in=bottom_attrib)\
        .filter(submission__connection__contact__emisreporter__schools__location__in=location.get_descendants(include_self=True).all())\
        .annotate(Sum('value_int')).values_list('value_int__sum', flat=True)

    if sum(bottom_value) > 0:
        return sum(top_value) / sum(bottom_value)
    else:
        return None


class SchoolMixin(object):
    SCHOOL_ID = 'submission__connection__contact__emisreporter__schools__pk'
    SCHOOL_NAME = 'submission__connection__contact__emisreporter__schools__name'

    def total_attribute_by_school(self, report, keyword, single_week=False):
        start_date = report.start_date
        if single_week:
            start_date = report.end_date - datetime.timedelta(7)

        return XFormSubmissionValue.objects.exclude(submission__has_errors=True)\
        .exclude(submission__connection__contact=None)\
        .filter(created__range=(start_date, report.end_date))\
        .filter(attribute__slug__in=keyword)\
        .filter(submission__connection__contact__emisreporter__schools__location__in=report.location.get_descendants(include_self=True).all())\
        .values(self.SCHOOL_NAME,
            self.SCHOOL_ID)\
        .annotate(Sum('value_int'))

    def total_dateless_attribute_by_school(self, report, keyword):
        return XFormSubmissionValue.objects.exclude(submission__has_errors=True)\
        .exclude(submission__connection__contact=None)\
        .filter(attribute__slug__in=keyword)\
        .filter(submission__connection__contact__emisreporter__schools__location__in=report.location.get_descendants(include_self=True).all())\
        .values(self.SCHOOL_NAME,
            self.SCHOOL_ID)\
        .annotate(Sum('value_int'))


    def num_weeks(self, report):
        if report.end_date == report.start_date:
            report.end_date = report.end_date + datetime.timedelta(days=1)
        td = report.end_date - report.start_date
        holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
        for start, end in holidays:
            if start > report.start_date and end < report.end_date:
                td -= (end - start)

                #        return td.days / 7
        return (td.days / 7) if ((td.days / 7) > 1) else 1


class AverageSubmissionBySchoolColumn(Column, SchoolMixin):
    def __init__(self, keyword, extra_filters=None):
        self.keyword = keyword
        self.extra_filters = extra_filters

    def add_to_report(self, report, key, dictionary):
        val = total_submissions(self.keyword, report.start_date, report.end_date, report.location, self.extra_filters)
        for rdict in val:
            rdict['value'] = rdict['value'] / locations.get(pk=rdict['location_id']).get_descendants(include_self=True).aggregate(Count('schools'))['schools__count']
        reorganize_location(key, val, dictionary)


class DateLessRatioColumn(Column, SchoolMixin):
    """
    This divides the total number of an indicator (for instance, boys yearly enrollment)
    by the total of another indicator (for instance, total classrooms)].

    This gives you the ratio between the two indicators, each of which
    are fixed yearly amounts (not dependent on date).
    """
    def __init__(self, top_attrib, bottom_attrib):
        if type(top_attrib) != list:
            top_attrib = [top_attrib]
        if type(bottom_attrib) != list:
            bottom_attrib = [bottom_attrib]
        self.top_attrib = top_attrib
        self.bottom_attrib = bottom_attrib

    def add_to_report(self, report, key, dictionary):
        top_val = self.total_dateless_attribute_by_school(report, self.top_attrib)
        bottom_val = self.total_dateless_attribute_by_school(report, self.bottom_attrib)

        bottom_dict = {}
        reorganize_dictionary('bottom', bottom_val, bottom_dict, self.SCHOOL_ID, self.SCHOOL_NAME, 'value_int__sum')
        val = []
        for rdict in top_val:
            if rdict[self.SCHOOL_ID] in bottom_dict:
                rdict['value_int__sum'] = (float(rdict['value_int__sum']) / bottom_dict[rdict[self.SCHOOL_ID]]['bottom'])
                val.append(rdict)

        reorganize_dictionary(key, val, dictionary, self.SCHOOL_ID, self.SCHOOL_NAME, 'value_int__sum')


class TotalAttributeBySchoolColumn(Column, SchoolMixin):

    def __init__(self, keyword, extra_filters=None):
        if type(keyword) != list:
            keyword = [keyword]
        self.keyword = keyword
        self.extra_filters = extra_filters

    def add_to_report(self, report, key, dictionary):
        val = self.total_attribute_by_school(report, self.keyword)
        reorganize_dictionary(key, val, dictionary, self.SCHOOL_ID, self.SCHOOL_NAME, 'value_int__sum')


class WeeklyAttributeBySchoolColumn(Column, SchoolMixin):

    def __init__(self, keyword, extra_filters=None):
        if type(keyword) != list:
            keyword = [keyword]
        self.keyword = keyword
        self.extra_filters = extra_filters

    def add_to_report(self, report, key, dictionary):
        val = self.total_attribute_by_school(report, self.keyword)
        num_weeks = self.num_weeks(report)
        for rdict in val:
            rdict['value_int__sum'] /= num_weeks
        reorganize_dictionary(key, val, dictionary, self.SCHOOL_ID, self.SCHOOL_NAME, 'value_int__sum')


class WeeklyPercentageColumn(Column, SchoolMixin):
    """
    This divides the total number of an indicator for one week (such as, boys weekly attendance)
    by the total of another indicator (for instance, boys yearly enrollment)].

    This gives you the % expected for two indicators,
    one that is reported on weekly (for the CURRENT WEEK)
    and the other which is a fixed total number.

    If invert is True, this column will evaluate to 100% - the above value.

    For example, if boys weekly attendance this week was 75%, setting invert to
    True would instead return 100 - 75 = 25%
    """
    def __init__(self, week_attrib, total_attrib, invert=False):
        if type(week_attrib) != list:
            week_attrib = [week_attrib]
        if type(total_attrib) != list:
            total_attrib = [total_attrib]
        self.week_attrib = week_attrib
        self.total_attrib = total_attrib
        self.invert = invert

    def add_to_report(self, report, key, dictionary):
        top_val = self.total_attribute_by_school(report, self.week_attrib, single_week=True)
        bottom_val = self.total_dateless_attribute_by_school(report, self.total_attrib)

        bottom_dict = {}
        reorganize_dictionary('bottom', bottom_val, bottom_dict, self.SCHOOL_ID, self.SCHOOL_NAME, 'value_int__sum')
        val = []
        for rdict in top_val:
            if rdict[self.SCHOOL_ID] in bottom_dict:
                rdict['value_int__sum'] = (float(rdict['value_int__sum']) / bottom_dict[rdict[self.SCHOOL_ID]]['bottom']) * 100
                if self.invert:
                    rdict['value_int__sum'] = 100 - rdict['value_int__sum']
                val.append(rdict)

        reorganize_dictionary(key, val, dictionary, self.SCHOOL_ID, self.SCHOOL_NAME, 'value_int__sum')


class AverageWeeklyTotalRatioColumn(Column, SchoolMixin):
    """
    This divides the total number of an indicator (such as, boys weekly attendance) by:
    [the number of non-holiday weeks in the date range * the total of another indicator
    (for instance, boys yearly enrollment)].

    This gives you the % expected for two indicators, one that is reported on weekly
    and the other which is a fixed total number.
    """
    def __init__(self, weekly_attrib, total_attrib):
        if type(weekly_attrib) != list:
            weekly_attrib = [weekly_attrib]
        if type(total_attrib) != list:
            total_attrib = [total_attrib]
        self.weekly_attrib = weekly_attrib
        self.total_attrib = total_attrib

    def add_to_report(self, report, key, dictionary):
        top_val = self.total_attribute_by_school(report, self.weekly_attrib)
        bottom_val = self.total_dateless_attribute_by_school(report, self.total_attrib)
        num_weeks = self.num_weeks(report)

        bottom_dict = {}
        reorganize_dictionary('bottom', bottom_val, bottom_dict, self.SCHOOL_ID, self.SCHOOL_NAME, 'value_int__sum')
        val = []
        for rdict in top_val:
            if rdict[self.SCHOOL_ID] in bottom_dict:
                rdict['value_int__sum'] = (float(rdict['value_int__sum']) / (bottom_dict[rdict[self.SCHOOL_ID]]['bottom'] * num_weeks)) * 100
                val.append(rdict)

        reorganize_dictionary(key, val, dictionary, self.SCHOOL_ID, self.SCHOOL_NAME, 'value_int__sum')


class SchoolReport(Report):

    def __init__(self, request, dates):
        try:
            self.location = get_location(request)
        except:
            pass
        if self.location is None:
            self.location = Location.tree.root_nodes()[0]
        Report.__init__(self, request, dates)


class PollsColumn(Column, SchoolMixin):
    def __init__(self, polls_list, title, order):
        if type(polls_list) != list:
            self.polls_list = [polls_list]
        else:
            self.polls_list = polls_list
        self.title = title
        self.order = order

    def add_to_report(self, report, key, dictionary):
        val = {}
        for p in self.polls_list:
            p_list = p.split('_')
            val['poll'] = p
            x = p_list[1].split('p')
            val['value'] = '%s %s%s' % (x[0].title(), 'P', x[1])
            print val


class WeeklyPollSchoolColumn(PollNumericResultsColumn, SchoolMixin):

    def __init__(self, poll_name, title, order, attrs=None):
        self.poll = polls.get(name=poll_name)
        self.attrs = attrs
        self.title = title
        self.order = order

    def add_to_report(self, report, key, dictionary):
        var = self.poll.get_numeric_report_data(location=report.location)
        for dict in var:
            loc_id = dict['location_id']
            dictionary.setdefault(loc_id, {'location_name': dict['location_name'],
                                           'diff': (dict['rght'] - dict['lft'])})
            report.columns = report.columns[0:len(report._columns) - 1]
            for flag, attrkey in self.VALUE_FLAGS:
                if self.attrs & flag:
                    dictionary[loc_id]["%s_%s" % (key, attrkey)] = dict["value_float__%s" % attrkey]
                    report.columns.append("%s_%s" % (key, attrkey))


class DatelessSchoolReport(Report):
    def __init__(self, request=None, dates=None):
        try:
            self.location = get_location_for_user(request.user)
        except:
            pass
        if self.location is None:
            self.location = Location.tree.root_nodes()[0]

        self.report = {}  # SortedDict()
        self.columns = []
        column_classes = Column.__subclasses__()
        for attrname in dir(self):
            val = getattr(self, attrname)
            if type(val) in column_classes:
                self.columns.append(attrname)
                val.add_to_report(self, attrname, self.report)

        self.report = flatten_list(self.report)


def school_last_xformsubmission(request, school_id):
    xforms = []
    scripted_polls = []
    for xform in XForm.objects.all():
        xform_values = XFormSubmissionValue.objects.exclude(submission__has_errors=True)\
            .exclude(submission__connection__contact=None)\
            .filter(submission__connection__contact__emisreporter__schools__pk=school_id)\
            .filter(submission__xform=xform)\
            .order_by('-created')\
            .annotate(Sum('value_int'))[:1]  # .values_list('submission__xform__name', 'value_int__sum', 'submission__connection__contact__name', 'submission__created')
        xforms.append((xform, xform_values))

    for script in Script.objects.exclude(slug='emis_autoreg'):
        for step in script.steps.all():
            resp = Response.objects.select_related().filter(poll=step.poll)\
                .filter(message__connection__contact__emisreporter__schools__pk=school_id)\
                .order_by('-date')[:1]
            scripted_polls.append((step.poll, resp))

    return {'xforms': xforms, 'scripted_polls': scripted_polls}


def messages(request):
    if request.user.get_profile().is_member_of('Admins'):
        messages = Message.objects.exclude(
            connection__identity__in = getattr(settings, 'MODEM_NUMBERS')
        ).filter(direction='I',
            connection__contact__emisreporter__reporting_location__in =\
            locations.get(name__iexact="Uganda").get_descendants(include_self=True).all()
        )
    else:
        user_location = get_location(request)
        messages = Message.objects.select_related()\
            .exclude(connection__identity__in=getattr(settings, 'MODEM_NUMBERS'))\
            .exclude(connection__in=Blacklist.objects.all().values_list('connection'))\
            .filter(direction='I',
                    connection__contact__emisreporter__reporting_location__in=
                    user_location.get_descendants(include_self=True).all())

    if request.GET.get('error_msgs'):
        error_messages =  messages.filter(poll_responses=None) | messages.filter(poll_responses__has_errors=True)
        return error_messages
    else:
        return messages

def error_messages(request):
    all_messages = messages(request).order_by('-date')
    erroneous_messages = all_messages.filter(poll_responses=None) | all_messages.filter(poll_responses__has_errors=True)
    minimum_length = 20
    interesting_messages = erroneous_messages.filter(text__regex=r'^.{' + str(minimum_length) + ',}$')
    return interesting_messages[0:5]

def error_messages_as_json(request):
    messages = error_messages(request)
    json = serialize("json", messages)
    return HttpResponse(content=json, mimetype='application/json')

def othermessages(request, district_id=None):
    user_location = get_location(request)
    #First we get all incoming messages
    messages = Message.objects.select_related()\
        .exclude(connection__identity__in=getattr(settings, 'MODEM_NUMBERS'))\
        .filter(direction='I',
                connection__contact__emisreporter__reporting_location__in=
                user_location.get_descendants(include_self=True).all())

    #Get only messages handled by rapidsms_xforms and the polls app (this exludes opt in and opt out messages)
    messages = messages.filter(Q(application=None) | Q(application__in=['rapidsms_xforms', 'poll']))

    #Exclude XForm submissions
    messages = messages.exclude(pk__in=XFormSubmission.objects.exclude(message=None).filter(has_errors=False).values_list('message__pk', flat=True))

    # Exclude Poll responses
    messages = messages.exclude(pk__in=Response.objects.exclude(message=None).filter(has_errors=False).values_list('message__pk', flat=True))

    return messages


def reporters(request, district_id=None):
    profile = request.user.get_profile()
    if profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        return EmisReporter.objects.exclude(
                    connection__id__in=Blacklist.objects.values_list('connection__id', flat=True),
                    connection__identity__in = getattr(settings, 'MODEM_NUMBERS')
            ).exclude(reporting_location = None).exclude(connection=None)
    else:
        user_location = get_location(request)
        return EmisReporter.objects.exclude(\
            connection__id__in=Blacklist.objects.values_list('connection__id', flat=True)).\
            filter(reporting_location__in= user_location.get_descendants(include_self=True))

# time slider based work
def education_responses_bp3(request, dates=None):
    """
    -> district, figures
    """
    locations = locations.filter(type='district').filter(pk__in =\
        EmisReporter.objects.values_list('reporting_location__pk',flat=True))
    to_ret = []
    if dates:
        date_dict = dates(request)
        start = date_dict.get('start')
        end = date_dict.get('end')
        for location in locations:
            to_ret.append([location, get_numeric_report_data('edtrac_boysp6_attendance',
                                                             locations=[location],
                                                             time_range=[start, end],
                                                             to_ret='sum')])
        return to_ret
    else:
        for location in locations:
            to_ret.append([location, get_numeric_report_data('edtrac_boysp6_attendance',
                                                             locations=[location],
                                                             time_range=[getattr(settings, 'SCHOOL_TERM_START'),
                                                                         getattr(settings, 'SCHOOL_TERM_END')],
                                                             to_ret='sum')])
        return to_ret


def schools(request, district_id=None):
    profile = request.user.get_profile()
    if profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials') or profile.is_member_of('Ministry Officials'):
        return schools # should we include all schools???
    else:
        user_location = get_location(request)
        return schools.filter(location__in=user_location.get_descendants(include_self=True).all())


#excel reports
def raw_data(request, district_id, dates, slugs, teachers=False):
    """
    function to produce data once an XForm slug is provided
    function is a WIP; tested for better optimization on DB
    currently to be used to get values based on grades; [p7, p6, p5,..., p1]
    """
    #    from .reports import get_location
    user_location = get_location(request, district_id)
    schools = all_schools.filter(location__in=user_location.get_descendants(include_self=True).all())
    schools = list(schools)
    values = XFormSubmissionValue.objects.select_related()\
        .exclude(submission__has_errors=True)\
        .filter(created__range=(dates.get('start'), dates.get('end')))\
        .filter(attribute__slug__in=slugs)\
        .filter(submission__connection__contact__emisreporter__schools__in=schools)\
        .order_by('submission__connection__contact__emisreporter__schools__name', '-created')\
        .values('submission__connection__contact__emisreporter__schools__name', 'value_int', 'created')
        #.annotate(Avg('value_int'))
    values = list(values)

    data = []
    i = 0
    while i < len(values):
        school_values = []
        school_values.append(values[i]['submission__connection__contact__emisreporter__schools__name'])
        school_values.append(values[i]['value_int'])
        total = values[i]['value_int']
        if teachers:
            for x in range(i, (i + 1)):
                try:
                    school_values.append(values[x]['value_int'])
                    total += values[x]['value_int']
                except IndexError:
                    school_values.append(0)
                try:
                    if x == (i):
                        school_values.append(total)
                        school_values.append(values[x]['created'])
                except:
                    pass
        else:
            for x in range(i, (i + 6)):
                try:
                    school_values.append(values[x]['value_int'])
                    total += values[x]['value_int']
                except IndexError:
                    school_values.append(0)
                try:
                    if x == (i + 5):
                        school_values.append(total)
                        school_values.append(values[x]['created'])
                except:
                    pass
        i += 6
        data.append(school_values)
    return data


def produce_curated_data():
    #chart data
    pass


def create_excel_dataset(request, start_date, end_date, district_id):
    """
    # for excelification
    for up to 6 districts
    a function to return some excel output from varying datasets
    """
    #This can be expanded for other districts using the rapidSMS locations models
    #CURRENT_DISTRICTS = Location.objects.filter(name__in=XFormSubmissionValue.objects.values_list('submission__connection__contact__reporting_location__name', flat=True)).order_by('name')

    #location = Location.tree.root_nodes()[0]
    if start_date is None:
        start_date, end_date = previous_calendar_week()
    else:
        start_split = start_date.split('-')
        end_split = end_date.split('-')
        start_date = datetime.datetime(int(start_split[0]), int(start_split[1]), int(start_split[2]))
        end_date = datetime.datetime(int(end_split[0]), int(end_split[1]), int(end_split[2]))

    dates = {'start': start_date, 'end': end_date}
    # initialize Excel workbook and set encoding
    book = xlwt.Workbook(encoding='utf8')

    def write_xls(sheet_name, headings, data):
        sheet = book.add_sheet(sheet_name)
        rowx = 0
        for colx, value in enumerate(headings):
            sheet.write(rowx, colx, value)
        sheet.set_panes_frozen(True)  # frozen headings instead of split panes
        sheet.set_horz_split_pos(rowx + 1)  # in general, freeze after last heading row
        sheet.set_remove_splits(True)  # if user does unfreeze, don't leave a split there
        for row in data:
            rowx += 1
            for colx, value in enumerate(row):
                try:
                    value = value.strftime("%d/%m/%Y")
                except:
                    pass
                sheet.write(rowx, colx, value)

    GRADES = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'Total', 'Date']
    # TODO these should probably be explicitly defined somewhere instead of
    # looping through GRADES four times. or at least do all formatting in one loop
    boy_attendance_slugs = ['boys_{}'.format(g) for g in GRADES]
    girl_attendance_slugs = ['girls_{}'.format(g) for g in GRADES]
    boy_enrolled_slugs = ['enrolledb_{}'.format(g) for g in GRADES]
    girl_enrolled_slugs = ['enrolledg_{}'.format(g) for g in GRADES]
    TEACHER_HEADERS = ['School', 'Female', 'Male', 'Total', 'Date']
    teacher_attendance_slugs = ['teachers_f', 'teachers_m']
    teacher_deploy_slugs = ['deploy_f', 'deploy_m']

    #Boys attendance
    headings = ["School"] + GRADES
    data_set = raw_data(request, district_id, dates, boy_attendance_slugs)
    write_xls("Attendance data for Boys", headings, data_set)

    #Girls attendance
    headings = ["School"] + GRADES
    data_set = raw_data(request, district_id, dates,  girl_attendance_slugs)
    write_xls("Attendance data for Girls", headings, data_set)

    #Teacher attendance
    headings = TEACHER_HEADERS
    data_set = raw_data(request, district_id, dates,  teacher_attendance_slugs, teachers=True)
    write_xls("Attendance data for Teachers", headings, data_set)

    #Boys enrollment
    headings = ["School"] + GRADES
    dates = {'start': datetime.datetime(datetime.datetime.now().year, 1, 1),
             'end': datetime.datetime.now()}
    data_set = raw_data(request, district_id, dates, boy_enrolled_slugs)
    write_xls("Enrollment data for Boys", headings, data_set)

    #Girls Enorllment
    headings = ["School"] + GRADES
    data_set = raw_data(request, district_id, dates,  girl_enrolled_slugs)
    write_xls("Enrollment data for Girls", headings, data_set)

    #Teacher deployment
    headings = TEACHER_HEADERS
    data_set = raw_data(request, district_id, dates,  teacher_deploy_slugs, teachers=True)
    write_xls("Teachers Deployment", headings, data_set)

    response = HttpResponse(mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=attendance_data.xls'
    book.save(response)
    return response


def get_month_day_range(date, **kwargs):
    """
    handy function to give as a date range
    """
    if not kwargs:
        last_day = date + relativedelta(day=1, months=+1, days=-1)
        first_day = date + relativedelta(day=1)
        #return a tuple in the list
        return [datetime.datetime(first_day.year, first_day.month, first_day.day, 8),
                datetime.datetime(last_day.year, last_day.month, last_day.day, 19)]
    else:
        """
        There are times we want to get a set of date ranges to work with

        attributes that this function takes include
            -> date (a datetime object)
            -> depth (how many months back this list should generate)
        """
        depth = int(kwargs.get('depth'))
        to_ret = []
        d = date
        i = 0
        while i < len(range(depth)):
            first_day = d + relativedelta(day=1)
            last_day = d + relativedelta(day=1, months=+1, days=-1)
            d += relativedelta(months=-1)
            i += 1
            to_ret.append([
                datetime.datetime(first_day.year, first_day.month, first_day.day, 8),
                datetime.datetime(last_day.year, last_day.month, last_day.day, 19)])

        return to_ret


def set_thur_wed_range(thursday):
    """
    Function that sets today { a thursday } range
    """
    # thursday to wednesday
    # however we want to change the weeknumber a bit to get a `new` thursday
    # move thursday to last week

    last_thursday = thursday - datetime.timedelta(days=7)
    # set times
    # 0800hrs EAT
    thursday_morning = datetime.datetime(last_thursday.year, last_thursday.month, last_thursday.day, 8, 0)
    wednesday = thursday_morning + datetime.timedelta(days=6)
    # 1900hrs
    wednesday_evening = datetime.datetime(wednesday.year, wednesday.month, wednesday.day, 19, 0)
    return thursday_morning,wednesday_evening


def get_day_range(today):
    #how many days is it to this Thursday
    if today.weekday() > 3:
        # offest today by a week from this Thursday
        today = (today - datetime.timedelta(days=today.weekday() - 3)) + datetime.timedelta(days=7)
        return set_thur_wed_range(today)
    elif today.weekday() < 3:
        # if day is a little earlier in the week
        new_date = today + datetime.timedelta(days=(3 - today.weekday()))
        return set_thur_wed_range(new_date)
    else:  # when today is Thursday
        return set_thur_wed_range(today + datetime.timedelta(days=7))


def get_week_date(depth=None, get_time=datetime.datetime.now):
    """
    get_week_date returns a range of weekly dates from today when not in holiday
    """
    now = get_time()
    # clean the hour
    now = now - datetime.timedelta(seconds=now.second)
    now = now - datetime.timedelta(minutes=now.minute)
    now = now - datetime.timedelta(microseconds=now.microsecond)
    if now.hour == 8:
        pass
    elif now.hour > 8:
        now = now - datetime.timedelta(hours=(now.hour - 8))
    else:
        now = now + datetime.timedelta(hours=(8 - now.hour))

    if depth:
        """
        Suppose you want a depth of 3 weeks worth of weekly ranges, all you need to do is set the depth

        A depth of zero defaults to what you'd get in `get_day_range(now)`
        """

        date_collection = []

        try:
            for wk in range(depth):
                date_collection.append(now - datetime.timedelta(days=(wk * 7)))

            to_ret = map(get_day_range, date_collection)

            return to_ret
        except TypeError:
            # TODO should this be logged?
            print "error"
    else:
        return get_day_range(now)

def get_weeks(now,depth=None):
    """
    get_week_date returns a range of weekly dates from today when not in holiday
    """
    # clean the hour
    now = now if (now.second == 0) else (now - datetime.timedelta(seconds=now.second))
    now = now if (now.minute == 0) else (now - datetime.timedelta(minutes=now.minute))
    now = now if (now.microsecond == 0) else (now - datetime.timedelta(microseconds=now.microsecond))
    if now.hour == 8:
        pass
    elif now.hour > 8:
        now = now - datetime.timedelta(hours=(now.hour - 8))
    else:
        now = now + datetime.timedelta(hours=(8 - now.hour))

    if depth:
        """
        Suppose you want a depth of 3 weeks worth of weekly ranges, all you need to do is set the depth

        A depth of zero defaults to what you'd get in `get_day_range(now)`
        """

        date_collection = []

        try:
            for wk in range(depth):
                date_collection.append(now - datetime.timedelta(days=(wk * 7)))

            to_ret = map(get_day_range, date_collection)

            return to_ret
        except TypeError:
            # TODO should this be logged?
            print "error"
    else:
        return get_day_range(now)



def month19to20(**kwargs):
    now = datetime.datetime.now()

    if kwargs:
        if 'depth' in kwargs:
            month_clustor = get_month_day_range(now, depth=now.month)
            i = 0
            collectible = []
            while i < len(month_clustor):
                first_month_range = month_clustor[i]  # first month range range ( current month on first iteration)
                first_month = first_month_range[0]

                if (i + 1) >= len(month_clustor):
                    second_month = datetime.datetime((first_month.year - 1), 12, 20)
                else:
                    second_month_range = month_clustor[i + 1]  # the month before this first one
                    second_month = second_month_range[0]

                collectible.append(
                    [
                        datetime.datetime(second_month.year, second_month.month, 19, 8),
                        datetime.datetime(first_month.year, first_month.month, 20, 19)
                    ]
                )
                i += 1
            return collectible
    else:
        current_month, month_before, month_before_before = get_month_day_range(now, depth=3)

        # 20th of last month
        c_month_q_start = datetime.datetime(month_before[0].year,
                                            month_before[0].month,
                                            (month_before[0].day + 19), 8)  # set for 8 o'clock in the morning

        # 19th of this month
        c_month_q_end = datetime.datetime(current_month[0].year,
                                          current_month[0].month,
                                          (current_month[0].day + 18), 19)  # set for 7 o'clock in the evening

        # the month before last month's 20th
        p_month_q_start = datetime.datetime(month_before_before[0].year,
                                            month_before_before[0].month,
                                            (month_before_before[0].day + 19), 8)  # set for 8 o'clock in the morning
        # previous month's 19th
        p_month_q_end = datetime.datetime(month_before[0].year,
                                          month_before[0].month,
                                          (month_before[0].day + 18), 19)  # set for 7 o'clock in the evening

        current_month_quota = [c_month_q_start, c_month_q_end]

        previous_month_quota = [p_month_q_start, p_month_q_end]

        # set `current_month` and `previous month`
        current_month, previous_month = current_month_quota, previous_month_quota

        return [current_month, previous_month]


def get_numeric_report_data(poll_name, location=None, time_range=None, to_ret=None, **kwargs):
    try:
        poll = polls.get(name=poll_name)
    except ObjectDoesNotExist:
        return 0
    entity_content = ContentType.objects.get_for_model(Response)
    if time_range:
        if location:
        # time filters
            if location.type.name == 'country':  # for views that have locations
                q = Value.objects.select_related()\
                    .filter(attribute__slug='poll_number_value',
                            entity_ct=entity_content,
                            entity_id__in=poll.responses
                                            .filter(date__range=time_range,
                                                    contact__reporting_location__in=location.get_descendants()
                                                    .filter(type='district'))).values('entity_ct')
            else:
                if 'school' in kwargs:
                    q = Value.objects.select_related()\
                        .filter(attribute__slug='poll_number_value',
                                entity_ct=entity_content,
                                entity_id__in=poll.responses
                                                .filter(date__range=time_range,
                                                        contact__in=kwargs.get('school').emisreporter_set.all(),
                                                        contact__reporting_location=kwargs.get('school').location)).values('entity_ct')
                else:
                    q = Value.objects.select_related()\
                        .filter(attribute__slug='poll_number_value',
                                entity_ct=entity_content,
                                entity_id__in=poll.responses
                                                .filter(date__range=time_range,
                                                        contact__reporting_location=location)).values('entity_ct')
        else:
            # casing point for kwargs=locations
            locations = kwargs.get('locations')
            if 'school' in kwargs:
                q = Value.objects.select_related()\
                    .filter(attribute__slug='poll_number_value',
                            entity_ct=entity_content,
                            entity_id__in=poll.responses
                                            .filter(date__range=time_range,
                                                    contact__in=kwargs.get('school').emisreporter_set.all())).values('entity_ct')

            elif ('locations' in kwargs) and (len(locations) == 1):
                q = Value.objects.select_related()\
                    .filter(attribute__slug='poll_number_value',
                            entity_ct=entity_content,
                            entity_id__in=poll.responses.filter(date__range=time_range, contact__reporting_location=locations[0])).values('entity_ct')
                # use-case designed in views #TODO clean up
            else:
                q = Value.objects.select_related()\
                    .filter(attribute__slug='poll_number_value',
                            entity_ct=entity_content,
                            entity_id__in=poll.responses.filter(date__range=time_range)).values('entity_ct')
    else:
        q = Value.objects.select_related()\
            .filter(attribute__slug='poll_number_value',
                    entity_ct=entity_content,
                    entity_id__in=poll.responses.all()).values('entity_ct')

    if to_ret:
        if not q:
            return 0
        else:
            if to_ret == 'sum':
                return q.annotate(Sum('value_float'))[0]['value_float__sum']
            elif to_ret == 'avg':
                return q.annotate(Avg('value_float'))[0]['value_float__avg']
            elif to_ret == 'std':
                return q.annotate(StdDev('value_float'))[0]['value_float__stddev']
            elif to_ret == 'max':
                return q.annotate(Max('value_float'))[0]['value_float__max']
            elif to_ret == 'min':
                return q.annotate(Min('value_float'))[0]['value_float__min']
            elif to_ret == 'q':
                return q
    else:
        return q.annotate(Sum('value_float'), Count('value_float'), Avg('value_float'),
                          StdDev('value_float'), Max('value_float'), Min('value_float'))


def poll_response_sum(poll_name, **kwargs):
    #TODO refactor name of method
    #TODO add poll_type to compute count of repsonses (i.e. how many YES' and No's do exist)
    """
    This computes the eav response value to a poll
    can also be used to filter by district and create a dict with
    district vs value
    """
    #TODO: provide querying by date too
    if kwargs:
        if ('month_filter' in kwargs):
            if (kwargs['month_filter'] not in ['biweekly', 'weekly', 'monthly', 'termly']) and ('location' not in kwargs):
                # when no location is provided { worst case scenario }
                to_ret = {}
                _locations = Location.objects.filter(type='district',\
                            name__in=EmisReporter.objects.values_list('reporting_location', flat=True)).distinct()
                _locations = list(_locations)
                for location in _locations:
                    to_ret[location.__unicode__()] = get_numeric_report_data(poll_name,
                                                                             location=location,
                                                                             time_range=get_month_day_range(datetime.datetime.now()),
                                                                             to_ret='sum')
                return to_ret

        # TODO make sure this is correct because this could be
        # shortcircuited in very odd ways: A and B and C or D
        # probably better to group with parenthesis like:
        # (A and B) and (C or D)
        # (A and B and C) or D
        if ('month_filter' in kwargs) and ('location' in kwargs) and ('ret_type' in kwargs) or ('months' in kwargs):
            #TODO support drilldowns
            now = datetime.datetime.now()
            #if role is Admin/Ministry/UNICEF then all districts will be returned
            # if role is DEO, then just the district will be returned
            locations = kwargs.get('location')
            if isinstance(locations, list) and len(locations) > 1:
                #for the curious case that location actually returns a list of locations
                locations = locations
            if isinstance(locations, Location):
                if locations.type.name == 'country':
                    locations = Location.objects.select_related().get(name=kwargs.get('location')).get_descendants().filter(type="district")
                    locations = list(locations)
                else:
                    locations = [locations]

            to_ret = {}

            if 'months' not in kwargs:
                for location in locations:
                    to_ret[location.__unicode__()] = get_numeric_report_data(poll_name,
                                                                             location=location,
                                                                             time_range=get_month_day_range(now),
                                                                             to_ret='sum')
            else:
                # only use this in views that expect date ranges greater than one month
                today = parse(commands.getoutput('date')).date()
                if kwargs.get('months') is not None:
                    month_ranges = []
                    for i in range(kwargs.get('months')):
                        month_ranges.append(get_month_day_range(dateutils.increment(today, months=-i)))

                for location in locations:
                    #to_ret is something like { 'Kampala' : [23, 34] } => ['current_month', 'previoius month']

                    to_ret[location.__unicode__()] = []  # empty list we populate in a moment
                    for month_range in month_ranges:
                        to_ret[location.__unicode__()]\
                            .append(get_numeric_report_data(poll_name,
                                                            location=location,
                                                            time_range=month_range,
                                                            to_ret='sum'))
##TODO --> fix sorting??
            if kwargs.get('ret_type') == list:
            #returning a sorted list of values
                #return a dictionary of values e.g. {'kampala': (<Location Kampala>, 34)}
                #pre-emptive sorting -> by largest -> returns a sorted list of tuples
                #TODO improve sorting
                to_ret = sorted(to_ret.iteritems(), key=operator.itemgetter(1))
                #initial structure is [('name', val1, val2) ]
                for name, val in to_ret:
                    val.append(Location.objects.select_related().filter(type="district").get(name__icontains=name))
                    # the last elements appear to be the largest
                to_ret.reverse()
                return to_ret

        if (kwargs.get('month_filter') == 'termly') and ('locations' in kwargs):
            # return just one figure/sum without all the list stuff
            return get_numeric_report_data(poll_name,
                                           location=kwargs.get('locations'),
                                           time_range=[getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')],
                                           to_ret='sum')

        if (kwargs.get('month_filter') == 'biweekly') and ('locations' in kwargs):
            # return just one figure/sum without all the list stuff
            # TODO fix to work with biweekly data
            return [0, 0]

        if (kwargs.get('month_filter') == 'monthly') and ('locations' in kwargs) or ('month20to19' in kwargs):
            if kwargs.get('month_20to19'):
            #                nxt_month = datetime.datetime(now.year, now.month+1, now.day)
                current_month, previous_month = month19to20()

            else:  # return just one figure/sum without all the list stuff
                current_month, previous_month = get_month_day_range(datetime.datetime.now(), depth=2)

            return [
                get_numeric_report_data(poll_name, locations=kwargs.get('locations'), time_range=current_month, to_ret='sum'),
                get_numeric_report_data(poll_name, locations=kwargs.get('locations'), time_range=previous_month, to_ret='sum')
            ]

        #date_week = [datetime.datetime.now()-datetime.timedelta(days=7), datetime.datetime.now()]

        date_week = get_week_date(depth=1)[0]
        if (kwargs.get('month_filter') == 'weekly') and ('locations' in kwargs):
            # return just one figure/sum without all the list stuff
            return get_numeric_report_data(poll_name,
                                           location=kwargs.get('location'),
                                           time_range=date_week,
                                           to_ret='sum')

        # for data coming in from a school
        #TODO -> tailor function to handle data from only a set of users
        if (kwargs.get('month_filter') == 'weekly') and ('school' in kwargs):
            school = kwargs.get('school')
            # return only sums of values from responses sent in by EMIS reporters in this school
            response_sum = get_numeric_report_data(poll_name,
                                                   time_range=date_week if ('date_week' not in kwargs) else list(kwargs.get('date_week')),
                                                   school=school,
                                                   to_ret='sum',
                                                   belongs_to='schools')

            if response_sum == 0:
                return '--'
            else:
                return response_sum
        #another hail mary shot
        # when the type of data is from a single school and monthly data is needed
        if (kwargs.get('month_filter') == 'monthly') and ('school' in kwargs):
            school = kwargs.get('school')
            response_sum = get_numeric_report_data(poll_name,
                                                   time_range=kwargs.get('month_range'),
                                                   school=school,
                                                   to_ret=kwargs.get('to_ret'),
                                                   belongs_to='schools')
            if response_sum == 0:
                return '--'
            else:
                return response_sum
    else:
        return get_numeric_report_data(poll_name)


def cleanup_sums(sums):
    try:
        diff = sums[1] - sums[0]
        percent = (100 * float(diff)) / sums[0]
    except ZeroDivisionError:
        percent = 0
    return percent


def cleanup_differences_on_poll(responses):
    """a function to clean up total poll sums from districts and compute a difference"""
    # use case --> on polls where a difference is needed between previous and current time epochs
    # this function also aggregates a Location wide-poll
    current_epoch_sum = []
    previous_epoch_sum = []
    for x, y in responses:
        current_epoch_sum.append(y[0][0])
        previous_epoch_sum.append(y[1][0])

    current_epoch_sum = sum(filter(None, current_epoch_sum))
    previous_epoch_sum = sum(filter(None, previous_epoch_sum))

    # difference
    try:
        percent = 100 * (current_epoch_sum - previous_epoch_sum) / float(previous_epoch_sum)
    except ZeroDivisionError:
        percent = 0
    return percent


def is_holiday(date1, dates):
    for date_start, date_end in dates:
        if isinstance(date_end, str):
            if date1 == date_start:
                return True
        elif date1 >= date_start and date1 <= date_end:
            return True
    return False


def poll_responses_past_week_sum(poll_name, **kwargs):

    """
    Function to the total number of responses in between this current week and the pastweek
     get the sum, find its total; add up values excluding NoneTypes

    Usage:
        >>> #returns poll for current week
        >>> poll_response_past_week_sum(Poll.objects.get(name="edtrac_boysp3_attendance"))
        >>> (23,6)
        ###############################################################################################################
        # This returns sums of responses for a number of weeks while returning them as ranges
        # NOTE: if you are looking to getting data that reflects 2 different weeks, then you have to set it up as 2
        ###############################################################################################################
        >>> poll_responses_past_week_sum(Poll.objects.get(name="edtrac_boysp3_attendance"), location="Kampala", weeks = 2)
        >>> (34, 23)
    """
    if kwargs:
        first_quota, second_quota = get_week_date(depth=kwargs.get('weeks'))
        #narrowing to location
        if 'locations' in kwargs:
            # week_before would refer to the week before week that passed
            if is_holiday(first_quota[0], getattr(settings, 'SCHOOL_HOLIDAYS')):
                sum_of_poll_responses_past_week = '--'
            else:
                sum_of_poll_responses_past_week = get_numeric_report_data(poll_name,
                                                                          locations=kwargs.get('locations'),
                                                                          time_range=first_quota,
                                                                          to_ret='sum')
            if is_holiday(second_quota[0], getattr(settings, 'SCHOOL_HOLIDAYS')):
                sum_of_poll_responses_week_before = '--'
            else:
                sum_of_poll_responses_week_before = get_numeric_report_data(poll_name,
                                                                            locations=kwargs.get('locations'),
                                                                            time_range=second_quota,
                                                                            to_ret='sum')

            return [sum_of_poll_responses_past_week, sum_of_poll_responses_week_before]

        elif 'locations' in kwargs:

            if is_holiday(first_quota[0], getattr(settings, 'SCHOOL_HOLIDAYS')):
                sum_of_poll_responses_past_week = '--'
            else:
                sum_of_poll_responses_past_week = get_numeric_report_data(poll_name,
                                                                          location=kwargs.get('location'),
                                                                          time_range=first_quota,
                                                                          to_ret='sum')

            if is_holiday(second_quota[0], getattr(settings, 'SCHOOL_HOLIDAYS')):
                sum_of_poll_responses_week_before = '--'
            else:
                sum_of_poll_responses_week_before = get_numeric_report_data(poll_name,
                                                                            location=kwargs.get('location'),
                                                                            time_range=second_quota,
                                                                            to_ret='sum')

            return [sum_of_poll_responses_past_week, sum_of_poll_responses_week_before]

        elif 'school' in kwargs:

            if is_holiday(first_quota[0], getattr(settings, 'SCHOOL_HOLIDAYS')):
                sum_of_poll_responses_past_week = '--'
            else:
                sum_of_poll_responses_past_week = get_numeric_report_data(poll_name,
                                                                          belongs_to='schools',
                                                                          school=kwargs.get('school'),
                                                                          time_range=first_quota,
                                                                          to_ret='sum')

            if is_holiday(second_quota[0], getattr(settings, 'SCHOOL_HOLIDAYS')):
                sum_of_poll_responses_week_before = '--'
            else:
                sum_of_poll_responses_week_before = get_numeric_report_data(poll_name,
                                                                            belongs_to='schools',
                                                                            school=kwargs.get('school'),
                                                                            time_range=second_quota,
                                                                            to_ret='sum')

            return [sum_of_poll_responses_past_week, sum_of_poll_responses_week_before]

    else:
        # getting country wide statistics
        first_quota, second_quota = get_week_date(depth=2)  # default week range to 1
        if is_holiday(first_quota[0], getattr(settings, 'SCHOOL_HOLIDAYS')):
            sum_of_poll_responses_past_week = '--'
        else:
            sum_of_poll_responses_past_week = get_numeric_report_data(poll_name,
                                                                      time_range=first_quota,
                                                                      to_ret='sum')

        if is_holiday(second_quota[0], getattr(settings, 'SCHOOL_HOLIDAYS')):
            sum_of_poll_responses_week_before = '--'
        else:
            sum_of_poll_responses_week_before = get_numeric_report_data(poll_name,
                                                                        time_range=second_quota,
                                                                        to_ret='sum')

        return sum_of_poll_responses_past_week, sum_of_poll_responses_week_before


def poll_responses_term(poll_name, to_ret=None, **kwargs):

    """
    Function to get the results of a poll between now and beginning of term (this is a broad spectrum poll)

    >>> poll_response_term(poll_name, belongs_to='location', locations=Location.objects.all())
    >>> ... returns responses that are broad

    Another example:

    >>> poll_response_term(poll_name, belongs_to="schools", school_id=5)
    >>> ... returns responses coming in from reporters in a particular school

    """

    #TODO -> numeric polls, categorical polls

    if kwargs.get('belongs_to') == 'location':
        if to_ret:
            return get_numeric_report_data(poll_name,
                                           locations=kwargs.get('locations'),
                                           time_range=[getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')],
                                           to_ret=to_ret)
        else:
            return get_numeric_report_data(poll_name,
                                           locations=kwargs.get('locations'),
                                           time_range=[getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')],
                                           to_ret='sum')

    elif kwargs.get('belongs_to') == 'schools':
        if 'to_ret' in kwargs:
            return get_numeric_report_data(poll_name,
                                           school=kwargs.get('school'),
                                           time_range=[getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')],
                                           to_ret=kwargs.get('to_ret'))
        else:
            # default to sum
            return get_numeric_report_data(poll_name,
                                           school=kwargs.get('school'),
                                           time_range=[getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')],
                                           to_ret='sum')


def curriculum_progress_list(poll_name, **kwargs):
    """
    This function gets the curriculum progress in a week of either schools in a location or just a school
    """
    if kwargs:
        if 'location' in kwargs:
            try:
                to_ret = get_numeric_report_data(poll_name,
                                                 to_ret='q',
                                                 location=kwargs.get('location'),
                                                 time_range=get_week_date()).values_list('value_float', flat=True)
                        # default to just the week running Thursday through Wednesday, the next week
                return to_ret
            except AttributeError:
                return 0

        elif 'school' in kwargs:
            try:
                return get_numeric_report_data(poll_name,
                                               to_ret='q',
                                               belongs_to='schools',
                                               school=kwargs.get('school'))\
                    .values_list('value_float', flat=True)
            except AttributeError:
                return 0

        elif kwargs.get('time_range'):
            try:
                return  get_numeric_report_data(poll_name,
                                                to_ret='q',
                                                time_range=get_week_date())\
                    .values_list('value_float', flat=True)
            except AttributeError:
                return 0
    else:
        x = list(get_numeric_report_data(poll_name, to_ret='q').values_list('value_float', flat=True))
        return x


def curriculum_progress_mode(data_list):
    stats = Statistics(data_list)
    mode = stats.mode
    if len(mode) == 0:
        return
    return mode[0][0]


def generate_deo_report(location_name=None):
    if location_name is None:
        return
    else:
        try:
            # attempt to get a district if the location is not of district type.
            all_locations = list(Location.objects.select_related().filter(name=location_name))  # locations with similar name
            if len(all_locations) > 1:
                for loc in all_locations.exclude(type="country"):
                    if loc.type == 'district':
                        location = loc
                        break
                    else:
                        # probably a county, subcounty or village by the same name as district
                        loc_ancestors = loc.get_ancestors()
                        location = [l for l in loc_ancestors if l.type == 'district'][0]  # pick off a district
                        break
            else:
                location = all_locations[0]
        # TODO this exception does not exist :)
        #except DoesNotExist:
        except Exception:
            return  # quit
    location_filter = Location.objects.filter(name=location_name).distinct()

    boys_p3_enrollment = Poll.objects.get(name="edtrac_boysp3_enrollment").responses.filter(contact__reporting_location__in=
                                                                                        location_filter)

    boys_p6_enrollment = Poll.objects.get(name="edtrac_boysp6_enrollment").responses.filter(contact__reporting_location__in=
                                                                                        location_filter)

    girls_p3_enrollment = Poll.objects.get(name="edtrac_girlsp3_enrollment").responses.filter(contact__reporting_location__in=
                                                                                              location_filter)

    girls_p6_enrollment = Poll.objects.get(name="edtrac_girlsp6_enrollment").responses.filter(contact__reporting_location__in=
                                                                                              location_filter)

    p3_enrollment = boys_p3_enrollment + girls_p3_enrollment
    p6_enrollment = boys_p6_enrollment + girls_p6_enrollment


    attendance_boysp3_past_week, attendance_boysp3_week_before = get_sum_of_poll_response_past_week(Poll.objects.get(name=
    "edtrac_boysp3_attendance"), location_name=location_name, weeks=2)

    attendance_boysp6_past_week, attendance_boysp6_week_before = get_sum_of_poll_response_past_week(Poll.objects.get(name=
    "edtrac_boysp6_attendance"), location_name=location_name, weeks=2)

    attendance_girlsp3_past_week, attendance_girlsp3_week_before = get_sum_of_poll_response_past_week(Poll.objects.get(name=
    "edtrac_girlsp3_attendance"), location_name = location_name, weeks=2)

    attendance_girlsp6_past_week, attendance_girlsp6_week_before = get_sum_of_poll_response_past_week(Poll.objects.get(name=
    "edtrac_girlsp6_attendance"), location_name = location_name, weeks=2)

    #TODO curriculum progress
    return (
        Connection.objects.filter(contact__emisreporter__groups__name="DEO",
                                  contact__reporting_location=location),  # we are sure that the contact for the DEO will be retrieved
        (
            {
                'P3 pupils': p3_enrollment - (attendance_boysp3_past_week + attendance_girlsp3_past_week),
                'P6 pupils': p6_enrollment - (attendance_boysp6_past_week + attendance_girlsp6_past_week)
            },
            {
                'P3 pupils': p3_enrollment - (attendance_boysp3_week_before + attendance_girlsp3_week_before),
                'P6 pupils': p6_enrollment - (attendance_boysp6_week_before + attendance_girlsp6_week_before)
            }
        )
    )


def compute_report_percent(actual_reports, expected_reports):
    try:
        return 100 * (actual_reports / expected_reports)
    except ZeroDivisionError:
        return 0


def get_count_response_to_polls(poll_queryset, location_name=None, **kwargs):

    if kwargs:
        # when no location is provided { worst case scenario }
        #choices = [0, 25, 50, 75, 100 ] <-- percentage
        choices = kwargs.get('choices')
        #initialize to_ret dict with empty lists
        to_ret = {}
        if location_name:
            catchment_area_pk = [Location.objects.filter(type='district').get(name=location_name).pk]  # as list
        else:
            catchment_area_pk = Location.objects.filter(type="district", name__in=
                EmisReporter.objects.exclude(reporting_location=None).values_list('reporting_location__name',
                    flat=True).distinct()).values_list('pk', flat=True)

        for location in Location.objects.filter(pk__in=catchment_area_pk).select_related():
            to_ret[location.__unicode__()] = []

        if kwargs.get('with_range') and kwargs.get('with_percent'):
            today = datetime.datetime.now()
            month_ranges = get_month_day_range(today, depth=today.month)
            month_ranges.reverse()

            final_ret = []

            for month_range in month_ranges:
                temp = []
                location = Location.objects.filter(type="district").get(name=to_ret.keys()[0])
                expected_reports = all_schools.filter(pk__in = EmisReporter.objects.select_related().exclude(schools = None).\
                    filter(reporting_location = location).values_list('schools__pk', flat=True)).count()
                resps = poll_queryset.responses.filter(contact__in=\
                            Contact.objects.filter(reporting_location= location),
                            date__range = month_range).select_related()

                resp_values = [r.eav.poll_number_value for r in resps]

                for choice in choices:
                    temp.append((choice, compute_report_percent(resp_values.count(choice), expected_reports)))
                # final_ret is a collection of monthly data
                final_ret.append(temp)

            return final_ret

        elif ('termly' in kwargs) and ('with_percent' in kwargs) and (kwargs.get('admin') is False):
            temp = []
            termly_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
            expected_reports = all_schools.filter(pk__in = EmisReporter.objects.select_related().exclude(schools = None).\
                filter(reporting_location = location).values_list('schools__pk', flat=True)).count()
            responses = poll_queryset.responses.filter(contact__in =\
                Contact.objects.filter(reporting_location = location), date__range = termly_range)
            all_vals =  [r.eav.poll_number_value for r in responses]
            vals = filter(None, all_vals)

            try:
                # TODO is this the correct calculation?
                correctly_answered = len(vals) * 100 / expected_reports
            except ZeroDivisionError:
                correctly_answered = 0

            for choice in choices:
                if choice == 404:
                    if len(to_ret.keys()) == len(choices) - 1:
                        total = len(vals)
                        #unknown or improperly answered responses
                        try:
                            # TODO is this the correct calculation?
                            to_ret[choice] = 100 * (len(all_vals) - total) / len(all_vals)
                        except ZeroDivisionError:
                            to_ret[choice] = 0
                else:
                    to_ret[choice] = compute_report_percent(vals.count(choice), len(all_vals))
            return {'to_ret': to_ret, 'correctly_answered': correctly_answered}

        elif kwargs.get('termly') and kwargs.get('with_percent') and kwargs.get('admin'):
            termly_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
            expected_reports = all_schools.filter(pk__in = EmisReporter.objects.exclude(schools = None).\
                values_list('schools__pk', flat=True)).select_related().count()
            responses = poll_queryset.responses.filter(date__range = termly_range).select_related()
            all_vals = [r.eav.poll_number_value for r in responses]
            vals = filter(None, all_vals)

            try:
                # TODO is this the correct calculation?
                correctly_answered = len(vals)*100 / len(all_vals)
            except ZeroDivisionError:
                correctly_answered = 0

            to_ret = {}

            for choice in choices:
                if choice == 404:
                    if len(to_ret.keys()) == len(choices) - 1:
                        total = len(vals)  # all responses with value #TODO -> identify correct and incorrect
                        #unknown or improperly answered responses
                        try:
                            # TODO is this the correct calculation?
                            to_ret[choice] = 100 * (len(all_vals) - total) / len(all_vals)
                        except ZeroDivisionError:
                            to_ret[choice] = 0
                else:
                    to_ret[choice] = compute_report_percent(vals.count(choice), len(all_vals))
            return {'to_ret': to_ret, 'correctly_answered': correctly_answered}

        else:
            for key in to_ret.keys():
                resps = poll_queryset.responses.filter(contact__in=
                    Contact.objects.filter(reporting_location=Location.objects.filter(type="district").get(name=key)).
                    select_related(), date__range=get_month_day_range(datetime.datetime.now())).select_related()

                resp_values = [r.eav.poll_number_value for r in resps if hasattr(r.eav, 'poll_number_value')]
                expected_reports = School.objects.filter(pk__in = EmisReporter.objects.exclude(schools = None).\
                    filter(reporting_location = Location.objects.filter(type="district").get(name=key)).\
                    values_list('schools__pk', flat=True)).count()
                for choice in choices:
                    to_ret[key].append((choice, compute_report_percent(resp_values.count(choice), expected_reports)))
            return to_ret


def get_responses_to_polls(**kwargs):
    #TODO with filter() we can pass extra arguments
    if kwargs:
        if 'poll_name' in kwargs:
            poll_name = kwargs['poll_name']
            #TODO filter poll by district, school or county (might wanna index this too)
            return get_sum_of_poll_response(Poll.objects.get(name=poll_name))
        #in cases where a list of poll names is passed, a dictionary is returned
        if 'poll_names' in kwargs:
            poll_names = kwargs['poll_names']
            responses = {}
            for poll in poll_names:
                responses[poll] = get_sum_of_poll_response(Poll.objects.get(name=poll))
            return responses  # can be used as context variable too


def return_absent_month(poll_name, enrollment, month_range, school=None):

    # enrollment is the name of Enrollment poll
    if school:
        avg = get_numeric_report_data(poll_name, time_range=month_range, to_ret='avg', school=school)
        current_enrollment = poll_responses_term(enrollment, school=school, belongs_to='schools')

        if avg == '--':
            return '--'
        else:
            try:
                return (100 * avg) / current_enrollment
            except ZeroDivisionError:
                return 0.0


def avg(list):
    try:
        return float(sum(list)) / len(list)
    except ZeroDivisionError:
        return 0

def return_absent(poll_name, enrollment, locations=None, school=None, **kwargs):
    """
    Handy function to get weekly figures for enrollment/deployment to get absenteism percentages;
    EMIS is about variances and differences, this not only returns values; it returns the percentage
    change too.

    Value returned:
            [<location>, <some_value1>, <some_value2>, <some_difference>]
    """
    to_ret = []
    if locations:
        enrollment_poll = Poll.objects.get(name=enrollment)

        for loc in locations:
            pre_ret = []
            pre_ret.append(loc)

            enrollment_schools_pks = enrollment_poll.responses\
                .filter(contact__reporting_location__name=loc.name).values_list('contact__emisreporter__schools__pk', flat=True)
            school_filter = {}
            _schools = all_schools.filter(pk__in=enrollment_schools_pks)
            for school in _schools:
                week_now_temp, week_before_temp = poll_responses_past_week_sum(enrollment_poll.name,
                    weeks=2, school=school, to_ret='sum')
                current_enrollment = poll_responses_term(enrollment_poll.name, belongs_to='schools', school=school)
#                print school, week_now_temp, week_before_temp, current_enrollment
                try:
                    percent_absent_now = 100 * (current_enrollment - week_now_temp) / current_enrollment
                except ZeroDivisionError:
                    percent_absent_now = '--'
                except:
                    percent_absent_now = '--'

                try:
                    percent_absent_before = 100 * (current_enrollment - week_before_temp) / current_enrollment
                except ZeroDivisionError:
                    percent_absent_before = '--'
                except:
                    percent_absent_before = '--'
                school_filter[school] = (percent_absent_now, percent_absent_before)
#            print loc, "schools", len(school_filter.values())
            now, before = [], []
            for now_temp, before_temp in school_filter.values():
                now.append(now_temp)
                before.append(before_temp)

            now = avg([x for x in now if x != '--'])
            before = avg([x for x in before if x != '--'])

            pre_ret.extend([now, before])

            x, y = pre_ret[-2:]

            try:
                diff = x - y
            except TypeError:
                diff = '--'

            # append value difference
            pre_ret.append(diff)
            to_ret.append(pre_ret)
        return to_ret

    if school and ('date_week' in kwargs):
        current_enrollment = poll_responses_term(enrollment, school=school, belongs_to='schools')
        in_class = poll_response_sum(poll_name, month_filter='weekly', date_week=kwargs.get('date_week'), school=school)
        print current_enrollment, in_class
        try:
            x = 100 * (current_enrollment - in_class) / current_enrollment
        except Exception as e:
            x = '--'
            print e
        return [x]

    else:
        now, before = poll_responses_past_week_sum(poll_name, weeks=2, school=school)
        current_enrollment = poll_responses_term(enrollment, school=school, belongs_to='schools')
        try:
            now_percentage = 100 * (current_enrollment - now) / current_enrollment
        except exceptions.ZeroDivisionError:
            now_percentage = '--'
        except:
            now_percentage = '--'

        try:
            before_percentage = 100 * (current_enrollment - before) / current_enrollment
        except exceptions.ZeroDivisionError:
            before_percentage = '--'
        except:
            before_percentage = '--'

        try:
            diff = now_percentage - before_percentage
        except TypeError:
            diff = '--'
        return [now_percentage, before_percentage, diff]


#### Excel reporting

def write_to_xls(sheet_name, headings, data, book=None):
    sheet = book.add_sheet(sheet_name)
    rowx = 0
    for colx, value in enumerate(headings):
        sheet.write(rowx, colx, value)
        sheet.set_panes_frozen(True)  # frozen headings instead of split panes
        sheet.set_horz_split_pos(rowx + 1)  # in general, freeze after last heading row
        sheet.set_remove_splits(True)  # if user does unfreeze, don't leave a split there
        for row in data:
            rowx += 1
            for colx, value in enumerate(row):
                try:
                    value = value.strftime("%d/%m/%Y")
                except:
                    pass
                sheet.write(rowx, colx, value)


def get_range_on_date(reporting_period, report_comment):
    if reporting_period == 'wk':
        return get_week_date(depth=2)[0]
    elif reporting_period == 't':
        return [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    elif reporting_period == 'mo':
        return get_month_day_range(report_comment.report_date)
