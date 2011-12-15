from django.conf import settings
from django.db.models import Count, Sum
from generic.reports import Column as Col, Report
from generic.utils import flatten_list
from rapidsms.contrib.locations.models import Location
from rapidsms_httprouter.models import Message
from django.db.models import Q
from script.models import Script
from rapidsms_xforms.models import XFormSubmissionValue, XForm, XFormSubmission
from uganda_common.reports import XFormSubmissionColumn, XFormAttributeColumn, PollNumericResultsColumn, PollCategoryResultsColumn, LocationReport, QuotientColumn, InverseQuotientColumn
from uganda_common.utils import total_submissions, reorganize_location, total_attribute_value, previous_calendar_month
from uganda_common.utils import reorganize_dictionary
from .models import EmisReporter
from poll.models import Response, Poll
from .models import School
from .utils import previous_calendar_week
import datetime

from generic.reporting.views import ReportView
from generic.reporting.reports import Column
from uganda_common.views import XFormReport

GRADES = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']

def get_location_for_user(user):
    return user.get_profile().location

def get_location(request, district_id):
    #location of current logged in user or selected district
    user_location = Location.objects.get(pk=district_id) if district_id else get_location_for_user(request.user)
#    if user_location == Location.tree.root_nodes()[0]:
#        user_location = Location.objects.get(name='Kaabong')
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


class AverageSubmissionBySchoolColumn(Col, SchoolMixin):
    def __init__(self, keyword, extra_filters=None):
        self.keyword = keyword
        self.extra_filters = extra_filters

    def add_to_report(self, report, key, dictionary):
        val = total_submissions(self.keyword, report.start_date, report.end_date, report.location, self.extra_filters)
        for rdict in val:
            rdict['value'] = rdict['value'] / Location.objects.get(pk=rdict['location_id']).get_descendants(include_self=True).aggregate(Count('schools'))['schools__count']
        reorganize_location(key, val, dictionary)


class DateLessRatioColumn(Col, SchoolMixin):
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


class TotalAttributeBySchoolColumn(Col, SchoolMixin):

    def __init__(self, keyword, extra_filters=None):
        if type(keyword) != list:
            keyword = [keyword]
        self.keyword = keyword
        self.extra_filters = extra_filters

    def add_to_report(self, report, key, dictionary):
        val = self.total_attribute_by_school(report, self.keyword)
        reorganize_dictionary(key, val, dictionary, self.SCHOOL_ID, self.SCHOOL_NAME, 'value_int__sum')


class WeeklyAttributeBySchoolColumn(Col, SchoolMixin):

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


class WeeklyPercentageColumn(Col, SchoolMixin):
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


class AverageWeeklyTotalRatioColumn(Col, SchoolMixin):
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
            self.location = get_location_for_user(request.user)
        except:
            pass
        if self.location is None:
            self.location = Location.tree.root_nodes()[0]
        Report.__init__(self, request, dates)


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
        column_classes = Col.__subclasses__()
        for attrname in dir(self):
            val = getattr(self, attrname)
            if type(val) in column_classes:
                self.columns.append(attrname)
                val.add_to_report(self, attrname, self.report)

        self.report = flatten_list(self.report)

def location_values(location, data_dicts):
    value = 0
    if location == Location.tree.root_nodes()[0]:
        for dict in data_dicts:
            if dict['value']:
                value +=dict['value']
    else:
        for dict in data_dicts:
            if dict['location_name'] == location.name:
                if dict['value']:
                    value = dict['value']
    return value if value else '-'

def attendance_stats(request, district_id=None):
    stats = []
    user_location = get_location(request, district_id)
    location = Location.tree.root_nodes()[0]
    start_date, end_date = previous_calendar_week()
    dates = {'start':start_date, 'end':end_date}
#    import pdb;pdb.set_trace()
    boys = ["boys_%s" % g for g in GRADES]
    values = total_attribute_value(boys, start_date=start_date, end_date=end_date, location=location)
    stats.append(('boys', location_values(user_location, values)))

    girls = ["girls_%s" % g for g in GRADES]
    values = total_attribute_value(girls, start_date=start_date, end_date=end_date, location=location)
    stats.append(('girls', location_values(user_location, values)))

    total_pupils = ["boys_%s" % g for g in GRADES] + ["girls_%s" % g for g in GRADES]
    values = total_attribute_value(total_pupils, start_date=start_date, end_date=end_date, location=location)
    attendance_ratio = location_values(user_location, values)
    stats.append(('total pupils', location_values(user_location, values)))

    enrolled_total = ["enrolledb_%s" % g for g in GRADES] + ["enrolledg_%s" % g for g in GRADES]
    values = total_attribute_value(enrolled_total, start_date=datetime.datetime(datetime.datetime.now().year, 1, 1), end_date=datetime.datetime.now(), location=location)
    if not type(location_values(user_location, values)) == str and not type(attendance_ratio) == str and location_values(user_location, values) > 0:
        attendance_ratio /= float(location_values(user_location, values))
    if type(attendance_ratio) == str:
        stats.append(('% absent', '-'))
    else:
        stats.append(('% absent', '%0.1f%%'%(100-(attendance_ratio * 100))))

    values = total_attribute_value("teachers_f", start_date=start_date, end_date=end_date, location=location)
    stats.append(('female teachers', location_values(user_location, values)))

    values = total_attribute_value("teachers_m", start_date=start_date, end_date=end_date, location=location)
    stats.append(('male teachers', location_values(user_location, values)))

    values = total_attribute_value(["teachers_f", "teachers_m"], start_date=start_date, end_date=end_date, location=location)
    attendance_ratio = location_values(user_location, values)
    stats.append(('total teachers', location_values(user_location, values)))
    
    enrolled_total = ["deploy_f", "deploy_m"]
    values = total_attribute_value(enrolled_total, start_date=datetime.datetime(datetime.datetime.now().year, 1, 1), end_date=datetime.datetime.now(), location=location)
    if not type(location_values(user_location, values)) == str and not type(attendance_ratio) == str and location_values(user_location, values) > 0:
        attendance_ratio /= float(location_values(user_location, values))
    if type(attendance_ratio) == str:
        stats.append(('% absent', '-'))
    else:
        stats.append(('% absent', '%0.1f%%'%(100-(attendance_ratio * 100))))
    res = {}
    res['dates'] = dates
    res['stats'] = stats
    return res

def enrollment_stats(request, district_id=None):
    stats = []
    user_location = get_location(request, district_id)
    location = Location.tree.root_nodes()[0]
#    start_date, end_date = previous_calendar_week()
    start_date = datetime.datetime(datetime.datetime.now().year, 1, 1)
    end_date = datetime.datetime.now()
    dates = {'start':start_date, 'end':end_date}
    boys = ["enrolledb_%s" % g for g in GRADES]
    values = total_attribute_value(boys, start_date=start_date, end_date=end_date, location=location)
    stats.append(('boys', location_values(user_location, values)))

    girls = ["enrolledg_%s" % g for g in GRADES]
    values = total_attribute_value(girls, start_date=start_date, end_date=end_date, location=location)
    stats.append(('girls', location_values(user_location, values)))

    total_pupils = ["enrolledb_%s" % g for g in GRADES] + ["enrolledg_%s" % g for g in GRADES]
    values = total_attribute_value(total_pupils, start_date=start_date, end_date=end_date, location=location)
    stats.append(('total pupils', location_values(user_location, values)))

    values = total_attribute_value("deploy_f", start_date=start_date, end_date=end_date, location=location)
    stats.append(('female teachers', location_values(user_location, values)))

    values = total_attribute_value("deploy_m", start_date=start_date, end_date=end_date, location=location)
    stats.append(('male teachers', location_values(user_location, values)))

    values = total_attribute_value(["deploy_f", "deploy_m"], start_date=start_date, end_date=end_date, location=location)
    stats.append(('total teachers', location_values(user_location, values)))
    
    headteachers = School.objects.filter(location__in=user_location.get_descendants(include_self=True)).count()
    stats.append(('total head teachers', headteachers))
    stats.append(('total schools', headteachers))

    res = {}
    res['dates'] = dates
    res['stats'] = stats
    return res

def headteacher_attendance_stats(request, district_id=None):
    stats = []
    user_location = get_location(request, district_id)    
    start_date, end_date = previous_calendar_week()
    dates = {'start':start_date, 'end':end_date}
    htpresent_yes = Poll.objects.get(name='emis_absence').responses.exclude(has_errors=True)\
                            .filter(date__range=(start_date, end_date))\
                            .filter(message__text__icontains='yes')\
                            .filter(message__connection__contact__emisreporter__reporting_location__in=user_location.get_descendants(include_self=True).all()).count()
    htpresent_no = Poll.objects.get(name='emis_absence').responses.exclude(has_errors=True)\
                            .filter(date__range=(start_date, end_date))\
                            .filter(message__text__icontains='no')\
                            .filter(message__connection__contact__emisreporter__reporting_location__in=user_location.get_descendants(include_self=True).all()).count()
    stats.append(('head teachers reported present', htpresent_yes if htpresent_yes else '-'))
    stats.append(('head teachers reported absent', htpresent_no if htpresent_no else '-'))
    tot = htpresent_yes + htpresent_no if (htpresent_yes + htpresent_no) else '-'
    stats.append(('total reports received', tot))
    num_schools = School.objects.filter(location__in=user_location.get_descendants(include_self=True)).count()
    if num_schools > 0 and type(htpresent_yes) == int:        
        htpresent_yes /= float(num_schools)
        perc_present = '%0.1f%%'%(htpresent_yes * 100)
    perc_present = perc_present if htpresent_yes else '-'
        
    if num_schools > 0 and type(htpresent_no) == int:        
        htpresent_no /= float(num_schools)
        perc_absent = '%0.1f%%'%(htpresent_no * 100)
    perc_absent = perc_absent if htpresent_no else '-'
    
    stats.append(('% present', perc_present))
    stats.append(('% absent', perc_absent))
    res = {}
    res['dates'] = dates
    res['stats'] = stats
    return res

def gem_htpresent_stats(request, district_id=None):
    stats = []
    user_location = get_location(request, district_id)
    location = Location.tree.root_nodes()[0]
    start_date, end_date = previous_calendar_month()
    dates = {'start':start_date, 'end':end_date}
    values = total_submissions("gemteachers", start_date=start_date, end_date=end_date, location=location, extra_filters={'eav__gemteachers_htpresent':1})
    gem_htpresent = location_values(user_location, values)
    stats.append(('head teachers reported present', gem_htpresent))
    values = total_submissions("gemteachers", start_date=start_date, end_date=end_date, location=location, extra_filters={'eav__gemteachers_htpresent':0})
    gem_htabsent = location_values(user_location, values)
    stats.append(('head teachers reported absent', gem_htabsent))
    if type(gem_htpresent) == int and type(gem_htabsent) == int:
        tot = gem_htpresent + gem_htabsent
    else:
        tot = gem_htpresent if type(gem_htpresent) == int else gem_htabsent  
    stats.append(('total reports received', tot))
    num_schools = School.objects.filter(location__in=user_location.get_descendants(include_self=True)).count()
    if num_schools > 0 and type(gem_htpresent) == int:        
        gem_htpresent /= float(num_schools)
        perc_present = '%0.1f%%'%(gem_htpresent * 100)
    perc_present = '-' if type(gem_htpresent) == str else perc_present
        
    if num_schools > 0 and type(gem_htabsent) == int:        
        gem_htabsent /= float(num_schools)
        perc_absent = '%0.1f%%'%(gem_htabsent * 100)
    perc_absent = '-' if type(gem_htabsent) == str else perc_absent
    
    stats.append(('% present', perc_present))
    stats.append(('% absent', perc_absent))
    res = {}
    res['dates'] = dates
    res['stats'] = stats
    return res

def abuse_stats(request, district_id=None):
    stats = []
    user_location = get_location(request, district_id)
    location = Location.tree.root_nodes()[0]
    start_date, end_date = previous_calendar_month()
    dates = {'start':start_date, 'end':end_date}
    values = total_attribute_value("gemabuse_cases", start_date=start_date, end_date=end_date, location=location)
    stats.append(('GEM reported abuse cases', location_values(user_location, values)))
    
    htabuse = Poll.objects.get(name='emis_abuse').responses.exclude(has_errors=True)\
                            .filter(date__range=(start_date, end_date))\
                            .filter(message__connection__contact__emisreporter__reporting_location__in=user_location.get_descendants(include_self=True).all())\
                            .values('eav_values__value_int')\
                            .annotate(Sum('eav_values__value_int')).values_list('eav_values__value_int__sum', flat=True)
    stats.append(('headteacher reported abuse cases', htabuse[0] if htabuse[0] else '-'))
    res = {}
    res['dates'] = dates
    res['stats'] = stats
    return res

def meals_stats(request, district_id=None):
    stats = []
    user_location = get_location(request, district_id)
    start_date, end_date = previous_calendar_month()
    dates = {'start':start_date, 'end':end_date}
    expected_strs = ['none', 'very few', 'few', 'less than half', 'more than half', 'very many']
    
    meals = Poll.objects.get(name='emis_meals').responses.exclude(has_errors=True)\
                            .filter(date__range=(start_date, end_date))\
                            .filter(message__connection__contact__emisreporter__reporting_location__in=user_location.get_descendants(include_self=True).all())\
                            .values('eav_values__value_text')\
                            .annotate(Count('eav_values__value_text'))
    for cat in expected_strs:
        num = 0
        for ct in meals:
            if ct['eav_values__value_text']:
                if ct['eav_values__value_text'].lower() == cat:
                    num += ct['eav_values__value_text__count']
        stats.append((cat, num if num else '-'))
    res = {}
    res['dates'] = dates
    res['stats'] = stats
    return res

def keyratios_stats(request, district_id=None):
    stats = {}
    user_location = get_location(request, district_id)
    start_date = datetime.datetime(datetime.datetime.now().year, 1, 1)
    end_date = datetime.datetime.now()
    dates = {'start':start_date, 'end':end_date}
    #pupil to teacher ratio
    top_attrib = ["enrolledb_%s" % g for g in GRADES] + ["enrolledg_%s" % g for g in GRADES]
    bottom_attrib = ["deploy_f", "deploy_m"]
    pupil_to_teacher_ratio = attrib_ratios(top_attrib, bottom_attrib, dates, user_location)
    if pupil_to_teacher_ratio:
        stats['Teacher to Pupil Ratio'] = '1:%s'%pupil_to_teacher_ratio
    else:
        stats['Teacher to Pupil Ratio'] = 'Not Available'
    #pupil to latrine ratio    
    top_attrib = ["enrolledb_%s" % g for g in GRADES] + ["enrolledg_%s" % g for g in GRADES]
    bottom_attrib = ["latrinesused_b", "latrinesused_g"]
    latrinesused_ratio = attrib_ratios(top_attrib, bottom_attrib, dates, user_location)
    if latrinesused_ratio:
        stats['Latrine to Pupil Ratio'] = '1:%s'%latrinesused_ratio
    else:
        stats['Latrine to Pupil Ratio'] = 'Not Available'
    #pupil to classroom ratio    
    top_attrib = ["enrolledb_%s" % g for g in GRADES] + ["enrolledg_%s" % g for g in GRADES]
    bottom_attrib = ["classroomsused_%s" % g for g in GRADES]
    pupil_to_classroom_ratio = attrib_ratios(top_attrib, bottom_attrib, dates, user_location)
    if pupil_to_classroom_ratio:
        stats['Classroom to Pupil Ratio'] = '1:%s'%pupil_to_classroom_ratio
    else:
        stats['Classroom to Pupil Ratio'] = 'Not Available'
    #Level of functionality of SMCs
    smc_meetings = Poll.objects.get(name='emis_meetings').responses.exclude(has_errors=True)\
                                        .filter(date__range=(start_date, end_date))\
                                        .filter(message__connection__contact__emisreporter__schools__location__in=user_location.get_descendants(include_self=True).all())\
                                        .values_list('eav_values__value_float', flat=True)
                                        
    smc_meetings_ratio = sum(smc_meetings)                                    
    total_schools = School.objects.filter(location__in=user_location.get_descendants(include_self=True).all()).count()
    if total_schools:
        smc_meetings_ratio /= total_schools
        stats['Level of Functionality of SMCs'] = '%.1f%%'%(smc_meetings_ratio*100)
    else:
        stats['Level of Functionality of SMCs'] = 'Not Available'

    return stats

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

def messages(request, district_id=None):
    user_location = get_location(request, district_id)
    return Message.objects.filter(connection__contact__emisreporter__reporting_location__in=user_location.get_descendants(include_self=True).all())


def othermessages(request, district_id=None):
    user_location = get_location(request, district_id)
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
    user_location = get_location(request, district_id)
    return EmisReporter.objects.filter(reporting_location__in=user_location.get_descendants(include_self=True).all())

def schools(request, district_id=None):
    user_location = get_location(request, district_id)
    return School.objects.filter(location__in=user_location.get_descendants(include_self=True).all())

def deo_alerts(request, district_id=None):
    alerts = []
    user_location = get_location(request, district_id)
    
    #schools that have not sent in pupil attendance data this week
    start_date, end_date = previous_calendar_week()
    responsive_schools = XFormSubmissionValue.objects.all()\
                        .filter(Q(submission__xform__keyword__icontains='boys')|Q(submission__xform__keyword__icontains='girls'))\
                        .filter(created__range=(start_date, end_date))\
                        .filter(submission__connection__contact__emisreporter__schools__location__in=user_location.get_descendants(include_self=True).all())\
                        .values_list('submission__connection__contact__emisreporter__schools__name', flat=True)
    schools = School.objects.filter(location__in=user_location.get_descendants(include_self=True).all())
    if schools.count() > 0:
        total_schools_ratio = schools.exclude(name__in=responsive_schools).count()
        total_schools_ratio /= float(schools.count())
        perc = '%0.1f%%'%(total_schools_ratio*100)
    alerts.append((schools.exclude(name__in=responsive_schools).count(), perc, 'did not submit pupil attendance reports this week'))
    
    #schools that have not sent in pupil enrollment data this year
    start_date = datetime.datetime(datetime.datetime.now().year, 1, 1)
    end_date = datetime.datetime.now()
    responsive_schools = XFormSubmissionValue.objects.all()\
                        .filter(Q(submission__xform__keyword__icontains='enrolledb')|Q(submission__xform__keyword__icontains='enrolledg'))\
                        .filter(created__range=(start_date, end_date))\
                        .filter(submission__connection__contact__emisreporter__schools__location__in=user_location.get_descendants(include_self=True).all())\
                        .values_list('submission__connection__contact__emisreporter__schools__name', flat=True)
    schools = School.objects.filter(location__in=user_location.get_descendants(include_self=True).all())
    if schools.count() > 0:
        total_schools_ratio = schools.exclude(name__in=responsive_schools).count()
        total_schools_ratio /= float(schools.count())
        perc = '%0.1f%%'%(total_schools_ratio*100)
    alerts.append((schools.exclude(name__in=responsive_schools).count(), perc, 'have not submitted pupil enrollment data this year'))
    
    #schools that have not sent in teacher deployment data
    responsive_schools = XFormSubmissionValue.objects.all()\
                        .filter(submission__xform__keyword__icontains='deploy')\
                        .filter(created__range=(start_date, end_date))\
                        .filter(submission__connection__contact__emisreporter__schools__location__in=user_location.get_descendants(include_self=True).all())\
                        .values_list('submission__connection__contact__emisreporter__schools__name', flat=True)
    schools = School.objects.filter(location__in=user_location.get_descendants(include_self=True).all())
    if schools.count() > 0:
        total_schools_ratio = schools.exclude(name__in=responsive_schools).count()
        total_schools_ratio /= float(schools.count())
        perc = '%0.1f%%'%(total_schools_ratio*100)
    alerts.append((schools.exclude(name__in=responsive_schools).count(), perc, 'have not submitted teacher deployment data this year'))
    return alerts

class AttendanceReport(SchoolReport):
    boys = WeeklyAttributeBySchoolColumn(["boys_%s" % g for g in GRADES])
    girls = WeeklyAttributeBySchoolColumn(["girls_%s" % g for g in GRADES])
    total_students = WeeklyAttributeBySchoolColumn((["girls_%s" % g for g in GRADES] + ["boys_%s" % g for g in GRADES]))
    percentage_students = AverageWeeklyTotalRatioColumn((["girls_%s" % g for g in GRADES] + ["boys_%s" % g for g in GRADES]), (["enrolledg_%s" % g for g in GRADES] + ["enrolledb_%s" % g for g in GRADES]))
    week_attrib = ["girls_%s" % g for g in GRADES] + ["boys_%s" % g for g in GRADES]
    total_attrib = ["enrolledb_%s" % g for g in GRADES] + ["enrolledg_%s" % g for g in GRADES]
    percentange_student_absentism = WeeklyPercentageColumn(week_attrib, total_attrib, True)
    male_teachers = WeeklyAttributeBySchoolColumn("teachers_m")
    female_teachers = WeeklyAttributeBySchoolColumn("teachers_f")
    total_teachers = WeeklyAttributeBySchoolColumn(["teachers_f", "teachers_m"])
    percentage_teacher = AverageWeeklyTotalRatioColumn(["teachers_f", "teachers_m"], ["deploy_f", "deploy_m"])
    week_attrib = ["teachers_f", "teachers_m"]
    total_attrib = ["deploy_f", "deploy_m"]
    percentange_teachers_absentism = WeeklyPercentageColumn(week_attrib, total_attrib, True)


class AbuseReport(SchoolReport):
    cases = TotalAttributeBySchoolColumn("gemabuse_cases")
    
class EnrollmentReport(SchoolReport):
    start_date = datetime.datetime(datetime.datetime.now().year, 1, 1)
    end_date = datetime.datetime.now()
    dates = {'start_date':start_date, 'end_date':end_date}
    girls = TotalAttributeBySchoolColumn(["girls_%s" % g for g in GRADES])
    boys = TotalAttributeBySchoolColumn(["boys_%s" % g for g in GRADES])
    total_pupils = TotalAttributeBySchoolColumn(["girls_%s" % g for g in GRADES] + ["boys_%s" % g for g in GRADES])
    female_teachers = TotalAttributeBySchoolColumn(["teachers_f"])
    male_teachers = TotalAttributeBySchoolColumn(["teachers_m"])
    total_teachers = TotalAttributeBySchoolColumn(["teachers_f", "teachers_m"])
    
class KeyRatiosReport(SchoolReport):
    pupils_to_teacher = DateLessRatioColumn(["girls_%s" % g for g in GRADES] + ["boys_%s" % g for g in GRADES] , ["enrolledb_%s" % g for g in GRADES] + ["enrolledg_%s" % g for g in GRADES])
    pupils_to_latrine = DateLessRatioColumn(["girls_%s" % g for g in GRADES] + ["boys_%s" % g for g in GRADES] , ["latrinesused_b", "latrinesused_g"])
    pupils_to_classroom = DateLessRatioColumn(["girls_%s" % g for g in GRADES] + ["boys_%s" % g for g in GRADES] , ["classroomsused_%s" % g for g in GRADES])
    
COLUMN_TITLE_DICT = {
    
}

class EmisSubmissionColumn(XFormSubmissionColumn):
    def get_title(self):
        return self.title or (COLUMN_TITLE_DICT[self.keyword] if self.keyword in COLUMN_TITLE_DICT else '')


class EmisAttributeColumn(XFormAttributeColumn):
    def get_title(self):
        tolookup = self.keyword
        if type(self.keyword) == list:
            tolookup = self.keyword[0]
        return self.title or (COLUMN_TITLE_DICT[tolookup] if tolookup in COLUMN_TITLE_DICT else '')
    
class TotalEnrollmentColumn(EmisAttributeColumn):
    start_date = datetime.datetime(datetime.datetime.now().year, 1, 1)
    end_date = datetime.datetime.now()  
    def add_to_report(self, report, key, dictionary):
        val = total_attribute_value(self.keyword, self.start_date, self.end_date, report.location, self.extra_filters)
        reorganize_location(key, val, dictionary)
    
class NewAttendanceReport(XFormReport):
    template_name = "education/partials/stats_base.html"

    def get_top_columns(self):
        return [
            ('Pupils Attendance', '/emis/pupils/', 5),
            ('Teachers Attendance', '/emis/teachers/', 5),
        ]

    boys = EmisAttributeColumn(["boys_%s" % g for g in GRADES], order=1, title='Boys', chart_title="Variation of Boys Attendance")
    girls = EmisAttributeColumn(["girls_%s" % g for g in GRADES], order=2, title='Girls', chart_title="Variation of Girls Attendance")
    total_pupils = EmisAttributeColumn(["boys_%s" % g for g in GRADES] + ["girls_%s" % g for g in GRADES], order=3, title='Total Pupils', chart_title="Variation of Total Pupil Attendance")
    total_enrollment = TotalEnrollmentColumn(["enrolledb_%s" % g for g in GRADES] + ["enrolledg_%s" % g for g in GRADES], order=4, title='Enrollment', chart_title="Variation of Total Pupil Enrollment")
    perc_pupils_absent = InverseQuotientColumn(total_pupils, total_enrollment, order=5, title='% Absent', chart_title="Variation of Pupil Absenteeism")
    males = EmisAttributeColumn("teachers_m", order=6, title='Males', chart_title="Variation of Male Teacher Attendance")
    females = EmisAttributeColumn("teachers_f", order=7, title='Females', chart_title="Variation of Female Teacher Attendance")
    total_teachers = EmisAttributeColumn(["teachers_f", "teachers_m"], order=8, title='Total Teachers', chart_title="Variation of Total Teacher Attendance")
    total_deployment = TotalEnrollmentColumn(["deploy_f", "deploy_m"], order=9, title='Deployment', chart_title="Variation of total Teacher Deployment")
    perc_teachers_absent = InverseQuotientColumn(total_teachers, total_deployment, order=10, title='% Absent', chart_title="Variation of Teacher Absenteeism")

    def get_default_column(self):
        return ('girls', self.girls)
    
    def get_total_enrolled(self):
        return EmisSubmissionColumn(["enrolledb_%s" % g for g in GRADES] + ["enrolledg_%s" % g for g in GRADES])
