from django.conf import settings
from django.db.models import Count, Sum
from generic.reports import Report
from generic.reporting.reports import Column
from generic.reporting.views import ReportView
from generic.utils import flatten_list
from rapidsms.contrib.locations.models import Location
from rapidsms_httprouter.models import Message
from django.db.models import Q
from script.models import Script
from rapidsms_xforms.models import XFormSubmissionValue, XForm, XFormSubmission
from uganda_common.reports import PollNumericResultsColumn, PollCategoryResultsColumn, LocationReport, QuotientColumn, InverseQuotientColumn
from uganda_common.utils import total_submissions, reorganize_location, total_attribute_value, previous_calendar_month
from uganda_common.utils import reorganize_dictionary
from education.utils import previous_calendar_week
from education.models import EmisReporter, School
from poll.models import Response, Poll
import datetime, dateutils
from types import NoneType
from rapidsms.models import Contact
from generic.reporting.views import ReportView
from generic.reporting.reports import Column
from uganda_common.views import XFormReport

GRADES = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']

def get_location_for_user(user):
    return user.get_profile().location

def get_location(request):
    #location of current logged in user or selected district
    district_id = request.POST.get('district_id') or request.GET.get('district_id')
    user_location = Location.objects.get(pk=district_id) if district_id else get_location_for_user(request.user)
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
        return td.days / 7 if td.days / 7 > 1 else 1


class AverageSubmissionBySchoolColumn(Column, SchoolMixin):
    def __init__(self, keyword, extra_filters=None):
        self.keyword = keyword
        self.extra_filters = extra_filters

    def add_to_report(self, report, key, dictionary):
        val = total_submissions(self.keyword, report.start_date, report.end_date, report.location, self.extra_filters)
        for rdict in val:
            rdict['value'] = rdict['value'] / Location.objects.get(pk=rdict['location_id']).get_descendants(include_self=True).aggregate(Count('schools'))['schools__count']
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
        self.poll = Poll.objects.get(name=poll_name)
        self.attrs = attrs
        self.title = title
        self.order = order

    def add_to_report(self, report, key, dictionary):
        var = self.poll.get_numeric_report_data(location=report.location)
        for dict in var:
            loc_id = dict['location_id']
            dictionary.setdefault(loc_id, {'location_name':dict['location_name'], 'diff':(dict['rght'] - dict['lft'])})
            report.columns = report.columns[0:len(report._columns) - 1]
            for flag, attrkey in self.VALUE_FLAGS:
                if self.attrs & flag:
                    dictionary[loc_name]["%s_%s" % (key, attrkey)] = dict["value_float__%s" % attrkey]
                    report.columns.append("%s_%s" % (key, attrkey))

class DatelessSchoolReport(Report):
    def __init__(self, request=None, dates=None):
        try:
            self.location = get_location_for_user(request.user)
        except:
            pass
        if self.location is None:
            self.location = Location.tree.root_nodes()[0]

        self.report = {} #SortedDict()
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
                       .annotate(Sum('value_int'))[:1] #.values_list('submission__xform__name', 'value_int__sum', 'submission__connection__contact__name', 'submission__created')
        xforms.append((xform, xform_values))

    for script in Script.objects.exclude(slug='emis_autoreg'):
        for step in script.steps.all():
            resp = Response.objects.filter(poll=step.poll)\
                   .filter(message__connection__contact__emisreporter__schools__pk=school_id)\
                   .order_by('-date')[:1]
            scripted_polls.append((step.poll,resp))

    return {'xforms':xforms, 'scripted_polls':scripted_polls}

def messages(request):
    user_location = get_location(request)
    messages = Message.objects.filter(direction='I', connection__contact__emisreporter__reporting_location__in=user_location.get_descendants(include_self=True).all())
    if request.GET.get('error_msgs'):
        #Get only messages handled by rapidsms_xforms and the polls app (this exludes opt in and opt out messages)
        messages = messages.filter(Q(application=None) | Q(application__in=['rapidsms_xforms', 'poll']))

        #Exclude XForm submissions
        messages = messages.exclude(pk__in=XFormSubmission.objects.exclude(message=None).filter(has_errors=False).values_list('message__pk', flat=True))

        # Exclude Poll responses
        return messages.exclude(pk__in=Response.objects.exclude(message=None).filter(has_errors=False).values_list('message__pk', flat=True))

    else:
        return messages


def othermessages(request, district_id=None):
    user_location = get_location(request)
    #First we get all incoming messages
    messages = Message.objects.filter(direction='I', connection__contact__emisreporter__reporting_location__in=user_location.get_descendants(include_self=True).all())

    #Get only messages handled by rapidsms_xforms and the polls app (this exludes opt in and opt out messages)
    messages = messages.filter(Q(application=None) | Q(application__in=['rapidsms_xforms', 'poll']))

    #Exclude XForm submissions
    messages = messages.exclude(pk__in=XFormSubmission.objects.exclude(message=None).filter(has_errors=False).values_list('message__pk', flat=True))

    # Exclude Poll responses
    messages = messages.exclude(pk__in=Response.objects.exclude(message=None).filter(has_errors=False).values_list('message__pk', flat=True))

    return messages

def reporters(request, district_id=None):
    user_location = get_location(request)
    return EmisReporter.objects.filter(reporting_location__in=user_location.get_descendants(include_self=True).all())

def schools(request, district_id=None):
    user_location = get_location(request)
    return School.objects.filter(location__in=user_location.get_descendants(include_self=True).all())

#excel reports
def raw_data(request, district_id, dates, slugs, teachers=False):
    """
    function to produce data once an XForm slug is provided
    function is a WIP; tested for better optimization on DB
    currently to be used to get values based on grades; [p7, p6, p5,..., p1]
    """
    #    from .reports import get_location
    user_location = get_location(request, district_id)
    schools = School.objects.filter(location__in=user_location.get_descendants(include_self=True).all())
    values = XFormSubmissionValue.objects.exclude(submission__has_errors=True)\
        .filter(created__range=(dates.get('start'), dates.get('end')))\
        .filter(attribute__slug__in=slugs)\
        .filter(submission__connection__contact__emisreporter__schools__in=schools)\
        .order_by('submission__connection__contact__emisreporter__schools__name','-created')\
        .values('submission__connection__contact__emisreporter__schools__name','value_int', 'created')
        #.annotate(Avg('value_int'))

    data = []
    i = 0
    while i < len(values):
        school_values = []
        school_values.append(values[i]['submission__connection__contact__emisreporter__schools__name'])
        school_values.append(values[i]['value_int'])
        total = values[i]['value_int']
        if teachers:
            for x in range(i,(i+1)):
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
            for x in range(i,(i+6)):
                try:
                    school_values.append(values[x]['value_int'])
                    total += values[x]['value_int']
                except IndexError:
                    school_values.append(0)
                try:
                    if x == (i+5):
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
    if start_date == None:
        start_date, end_date = previous_calendar_week()
    else:
        start_split = start_date.split('-')
        end_split = end_date.split('-')
        start_date = datetime.datetime(int(start_split[0]), int(start_split[1]), int(start_split[2]))
        end_date = datetime.datetime(int(end_split[0]), int(end_split[1]), int(end_split[2]))

    dates = {'start':start_date, 'end':end_date}
    # initialize Excel workbook and set encoding
    book = xlwt.Workbook(encoding='utf8')

    def write_xls(sheet_name, headings, data):
        sheet = book.add_sheet(sheet_name)
        rowx = 0
        for colx, value in enumerate(headings):
            sheet.write(rowx, colx, value)
        sheet.set_panes_frozen(True) # frozen headings instead of split panes
        sheet.set_horz_split_pos(rowx+1) # in general, freeze after last heading row
        sheet.set_remove_splits(True) # if user does unfreeze, don't leave a split there
        for row in data:
            rowx += 1
            for colx, value in enumerate(row):
                try:
                    value = value.strftime("%d/%m/%Y")
                except:
                    pass
                sheet.write(rowx, colx, value)

    GRADES = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'Total', 'Date']
    boy_attendance_slugs = ['boys_%s'% g for g in GRADES]
    girl_attendance_slugs = ['girls_%s'%g for g in GRADES]
    boy_enrolled_slugs = ["enrolledb_%s"%g for g in GRADES]
    girl_enrolled_slugs = ["enrolledg_%s"%g for g in GRADES]
    TEACHER_HEADERS = ['School', 'Female', 'Male', 'Total', 'Date']
    teacher_attendance_slugs = ['teachers_f', 'teachers_m']
    teacher_deploy_slugs = ['deploy_f', 'deploy_m']

    #Boys attendance
    headings = ["School"] + GRADES
    data_set = raw_data(request, district_id, dates, boy_attendance_slugs)
    write_xls("Attendance data for Boys",headings,data_set)

    #Girls attendance
    headings = ["School"] + GRADES
    data_set = raw_data(request, district_id, dates,  girl_attendance_slugs)
    write_xls("Attendance data for Girls",headings,data_set)

    #Teacher attendance
    headings = TEACHER_HEADERS
    data_set = raw_data(request, district_id, dates,  teacher_attendance_slugs, teachers=True)
    write_xls("Attendance data for Teachers",headings,data_set)

    #Boys enrollment
    headings = ["School"] + GRADES
    dates = {'start':datetime.datetime(datetime.datetime.now().year, 1, 1), 'end':datetime.datetime.now()}
    data_set = raw_data(request, district_id, dates, boy_enrolled_slugs)
    write_xls("Enrollment data for Boys",headings,data_set)

    #Girls Enorllment
    headings = ["School"] + GRADES
    data_set = raw_data(request, district_id, dates,  girl_enrolled_slugs)
    write_xls("Enrollment data for Girls",headings,data_set)

    #Teacher deployment
    headings = TEACHER_HEADERS
    data_set = raw_data(request, district_id, dates,  teacher_deploy_slugs, teachers=True)
    write_xls("Teachers Deployment",headings,data_set)

    response = HttpResponse(mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=attendance_data.xls'
    book.save(response)
    return response

def get_month_day_range(date, **kwargs):
    """
    handy function to give as a date range
    """
    import datetime
    from dateutil.relativedelta import relativedelta
    if not kwargs:
        last_day = date + relativedelta(day = 1, months =+ 1, days =- 1)
        first_day = date + relativedelta(day = 1)
        #return a tuple in the list
        return [first_day, last_day]
    else:
        """
        There are times we want to get a set of date ranges to work with

        attributes that this function takes include
            -> date (a datetime object)
            -> depth (how many months back this list should generate)
        """
        depth = int(kwargs.get('depth'))
        to_ret = []
        for i in range(depth):
            date -= relativedelta(months=i)
            last_day = date + relativedelta(day = 1, months =+ 1, days =- 1)
            first_day = date + relativedelta(day = 1)
            to_ret.append((first_day, last_day))
        return to_ret

def get_week_date(number=None):
    #TODO: scope out how well to get ``number`` generic
    from dateutil.relativedelta import relativedelta
    if number is not None:
        now = datetime.datetime.now()
        current_week_before_date = now + relativedelta(day=1, days =- number*7)
        past_week_before_date = current_week_before_date + relativedelta(day=1, days =- 7)
        return ([past_week_before_date, current_week_before_date], [current_week_before_date, now])
    return


def get_sum_of_poll_response(poll_queryset, **kwargs):
    #TODO refactor name of method
    #TODO add poll_type to compute count of repsonses (i.e. how many YES' and Nos do exist)
    """
    This computes the eav response value to a poll
    can also be used to filter by district and create a dict with
    district vs value
    """
    #TODO: provide querying by date too
    s = 0
    if kwargs:
        if kwargs.has_key('month_filter') and not kwargs.get('month_filter') == 'termly' and not kwargs.has_key('location'):
            # when no location is provided { worst case scenario }
            DISTRICT = ['Kaabong', 'Kabarole', 'Kyegegwa', 'Kotido']
            to_ret = {}
            for location in Location.objects.filter(type="district", name__in=DISTRICT):
                resps = poll_queryset.responses.filter(contact__in=\
                Contact.objects.filter(reporting_location=location),
                    date__range = get_month_day_range(datetime.datetime.now())
                )
                resp_values = [r.eav.poll_number_value for r in resps]
                s = sum(filter(None, resp_values))
                to_ret[location.__unicode__()] = s
            return to_ret

        elif kwargs.get('month_filter') and kwargs.has_key('location') and\
           kwargs.has_key('ret_type') or kwargs.has_key('months'):
            #TODO support drilldowns
            now = datetime.datetime.now()
            #if role is Admin/Ministry/UNICEF then all districts will be returned
            # if role is DEO, then just the district will be returned
            if kwargs.get('location').type.name == 'country':
                locations = Location.objects.get(name=kwargs.get('location')).get_descendants().filter(type="district")
            else:
                locations = [location]
            to_ret = {}
            if not kwargs.has_key('months'):
                for location in locations:
                    resps = poll_queryset.responses.filter(
                        contact__in = Contact.objects.filter(reporting_location=location),
                        date__range = get_month_day_range(now)
                    )
                    #for Demo purposes compute total from messages
                    resp_values = [r.eav.poll_number_value for r in resps]
                    to_ret[location.__unicode__()] = [sum(filter(None, resp_values))]
            else:
                # only use this in views that expect date ranges greater than one month
                from dateutil.parser import parse
                import commands, dateutils
                today = parse(commands.getoutput('date')).date()
                month_ranges = [
                get_month_day_range(dateutils.increment(today, months=-i))
                for i in range(int(kwargs.get('months')))
                ]

                for location in locations:
                    to_ret[location.__unicode__()] = [] #empty list we populate in a moment
                    for month_range in month_ranges:
                        resps = poll_queryset.responses.filter(
                            contact__in = Contact.objects.filter(reporting_location=location),
                            date__range = month_range)
                        resp_values = [r.eav.poll_number_value for r in resps]
                        sum_of_values = sum(filter(None, resp_values))
                        # Averaging function
                        if kwargs.get('action') == 'avg' and kwargs.has_key('action'):
                            # for some cases, we need to compute an average of the response values
                            count = resps.count()
                            try:
                                to_ret[location.__unicode__()].append((float(sum_of_values)/count, month_range[0]))
                            except ZeroDivisionError:
                                # dividing by zero means we have no values/reports on that month from the EMIS reporter
                                to_ret[location.__unicode__()].append((0, month_range[0]))
                        else:
                            #to_ret is something like { 'Kampala' : [23, 34] } => ['current_month', 'previoius month']
                            to_ret[location.__unicode__()].append((sum_of_values, month_range[0]))
            if kwargs.get('ret_type') == list:
                    #returning a sorted list of values
                import operator
                #return a dictionary of values e.g. {'kampala': (<Location Kampala>, 34)}
                #pre-emptive sorting -> by largest -> returns a sorted list of tuples
                #TODO improve sorting
                to_ret = sorted(to_ret.iteritems(), key=operator.itemgetter(1))
                #initial structure is [('name', val1, val2) ]
                for name, val in to_ret:
                    val.append(Location.objects.filter(type="district").get(name__icontains=name))
                    # the last elements appear to be the largest
                to_ret.reverse()
                return to_ret
                #TODO Other data type returns.

        elif kwargs.get('month_filter')=='termly' and kwargs.has_key('locations'):
            # return just one figure/sum without all the list stuff
            return sum(
                filter(None,
                [
                    r.eav.poll_number_value for r in poll_queryset.responses.filter(
                    contact__in=Contact.objects.filter(reporting_location__in=kwargs.get('locations')),
                    date_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
                )
                ])
            )
    else:
        return sum(filter(None, [r.eav.poll_number_value for r in poll_queryset.responses.all()]))


def cleanup_differences_on_poll(responses):
    """a function to clean up total poll sums from districts and compute a difference"""
    #use case --> on polls where a difference is needed between previous and current month
    # this function also aggregates a Location wide-poll
    current_month_sum = []
    previous_month_sum = []
    for x, y in responses:
        current_month_sum.append(y[0][0])
        previous_month_sum.append(y[1][0])

    current_month_sum = sum(filter(None, current_month_sum))
    previous_month_sum = sum(filter(None, previous_month_sum))

    # difference
    try:
        percent = 100 * (current_month_sum - previous_month_sum) / float(previous_month_sum)
    except ZeroDivisionError:
        percent = 0
    return percent

def get_sum_of_poll_response_past_week(poll_queryset, **kwargs):
    """
    Function to the total number of responses in between this current week and the pastweek
     get the sum, find its total; add up values excluding NoneTypes

    Usage:
        >>> #returns poll for current week
        >>> get_sum_of_poll_response_past_week(Poll.objects.get(name="edtrac_boysp3_attendance"))
        >>> (23,6)

        >>>> # this returns sums of responses for a number of weeks while returning them as reanges
        >>> get_sum_of_poll_response_past_week(Poll.objects.get(name="edtrac_boysp3_attendance"),
        .... location="Kampala", weeks=1)
        >>> (34, 23)
    """

    if kwargs:
        first_quota, second_quota = get_week_date(number=kwargs.get('weeks'))
        #narrowing to location
        if kwargs.has_key('locations'):
            sum_of_poll_responses_week_before = sum(filter(None, [r.eav.poll_number_value for r in poll_queryset.responses.filter(
                date__range = first_quota,
                contact__in =\
                Contact.objects.filter(reporting_location__in=kwargs.get('locations')))]))

            sum_of_poll_responses_past_week = sum(filter(None,
                [
                r.eav.poll_number_value for r in poll_queryset.responses.filter(date__range = second_quota,
                    contact__in =\
                    Contact.objects.filter(reporting_location__in=kwargs.get('locations')))]))
    else:
        # getting country wide statistics
        first_quota, second_quota = get_week_date(number=1) # default week range to 1
        sum_of_poll_responses_week_before = sum(filter(None, [r.eav.poll_number_value
                                                              for r in poll_queryset.responses.filter(
            date__range = first_quota,
            contact__in = Contact.objects.all())]))
        sum_of_poll_responses_past_week = sum(filter(None,[r.eav.poll_number_value
                                                           for r in poll_queryset.responses.filter(
            date__range = second_quota,
            contact__in = Contact.objects.all())]))

    return sum_of_poll_responses_past_week, sum_of_poll_responses_week_before

def get_sum_of_poll_response_since_beginning_of_term(poll_queryset, **kwargs):
    """
    Function to get the results of a poll between now and beginning of term
    """
    #TODO -> numeric polls, categorical polls
    pass

def generate_deo_report(location_name = None):
    from rapidsms.models import Connection

    if location_name is None:
        return
    else:
        try:
            # attempt to get a district if the location is not of district type.
            all_locations = Location.objects.filter(name=location_name) # locations with similar name
            if len(all_locations) > 1:
                for loc in all_locations.exclude(type="country"):
                    if loc.type == 'district':
                        location = loc
                        break
                    else:
                        # probably a county, subcounty or village by the same name as district
                        loc_ancestors = loc.get_ancestors()
                        location = [l for l in loc_ancestors if l.type == 'district'][0] # pick off a district
                        break
            else:
                location = all_locations[0]
        except DoesNotExist:
            return #quit
    boys_p3_enrollment = Poll.objects.get(name="edtrac_p3_enrollment").responses.filter(contact__reporting_location__in=\
    Location.objects.filter(name=location_name).distinct())

    boys_p6_enrollment = Poll.objects.get(name="edtrac_p6_enrollment").responses.filter(contact__reporting_location__in=\
    Location.objects.filter(name=location_name).distinct())

    girls_p3_enrollment = Poll.objects.get(name="edtrac_girlsp3_enrollment").responses.filter(contact__reporting_location__in=\
    Location.objects.filter(name=location_name).distinct())

    girls_p6_enrollment = Poll.objects.get(name="edtrac_girlsp6_enrollment").responses.filter(contact__reporting_location__in=\
    Location.objects.filter(name=location_name).distinct())

    p3_enrollment = boys_p3_enrollment + girls_p3_enrollment
    p6_enrollment = boys_p6_enrollment + girls_p6_enrollment


    attendance_boysp3_past_week, attendance_boysp3_week_before = get_sum_of_poll_response_past_week(Poll.objects.get(name=\
    "edtrac_boysp3_attendance"), location_name = location_name, weeks=1)

    attendance_boysp6_past_week, attendance_boysp6_week_before = get_sum_of_poll_response_past_week(Poll.objects.get(name=\
    "edtrac_boysp6_attendance"), location_name = location_name, weeks=1)

    attendance_girlsp3_past_week, attendance_girlsp3_week_before = get_sum_of_poll_response_past_week(Poll.objects.get(name=\
    "edtrac_girlsp3_attendance"), location_name = location_name, weeks=1)

    attendance_girlsp6_past_week, attendance_girlsp6_week_before = get_sum_of_poll_response_past_week(Poll.objects.get(name=\
    "edtrac_girlsp6_attendance"), location_name = location_name, weeks=1)



    #TODO curriculum progress
    return (
        Connection.objects.filter(contact__emisreporter__groups__name="DEO",\
            contact__reporting_location = location), # we are sure that the contact for the DEO will be retrieved
        (
                {
                'P3 pupils' : p3_enrollment - (attendance_boysp3_past_week + attendance_girlsp3_past_week),
                'P6 pupils' : p6_enrollment - (attendance_boysp6_past_week + attendance_girlsp6_past_week)
            },
                {
                'P3 pupils' : p3_enrollment - (attendance_boysp3_week_before + attendance_girlsp3_week_before),
                'P6 pupils' : p6_enrollment - (attendance_boysp6_week_before + attendance_girlsp6_week_before)
            }
            )
        )

def get_count_response_to_polls(poll_queryset, **kwargs):
    if kwargs.has_key('month_filter') and kwargs.get('month_filter') and not kwargs.has_key('location') and kwargs.has_key('choices'):
        # when no location is provided { worst case scenario }
        DISTRICT = ['Kaabong', 'Kabarole', 'Kyegegwa', 'Kotido']
        #choices = [0, 25, 50, 75, 100 ] <-- percentage
        choices = kwargs.get('choices')
        #initialize to_ret dict with empty lists
        to_ret = {}
        for location in Location.objects.filter(type="district", name__in=DISTRICT):
            to_ret[location.__unicode__()] = []

        for key in to_ret.keys():
            resps = poll_queryset.responses.filter(contact__in=\
            Contact.objects.filter(reporting_location=Location.objects.filter(type="district").get(name=key)),
                date__range = get_month_day_range(datetime.datetime.now())
            )
            resp_values = [r.eav.poll_number_value for r in resps]
            for choice in choices:
                to_ret[key].append((choice, resp_values.count(choice)))
        return to_ret

def get_responses_to_polls(**kwargs):
    #TODO with filter() we can pass extra arguments
    if kwargs:
        if kwargs.has_key('poll_name'):
            poll_name = kwargs['poll_name']
            #TODO filter poll by district, school or county (might wanna index this too)
            return get_sum_of_poll_response(Poll.objects.get(name=poll_name))
            #in cases where a list of poll names is passed, a dictionary is returned
        if kwargs.has_key('poll_names'):
            poll_names = kwargs['poll_names']
            responses = {}
            for poll in poll_names:
                responses[poll] = get_sum_of_poll_response(Poll.objects.get(name=poll))
            return responses #can be used as context variable too

def write_to_xls(sheet_name, headings, data):
    sheet = book.add_sheet(sheet_name)
    rowx = 0
    for colx, value in enumerate(headings):
        sheet.write(rowx, colx, value)
        sheet.set_panes_frozen(True) # frozen headings instead of split panes
        sheet.set_horz_split_pos(rowx+1) # in general, freeze after last heading row
        sheet.set_remove_splits(True) # if user does unfreeze, don't leave a split there
        for row in data:
            rowx += 1
            for colx, value in enumerate(row):
                try:
                    value = value.strftime("%d/%m/%Y")
                except:
                    pass
                sheet.write(rowx, colx, value)