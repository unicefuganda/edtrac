from django import template
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rapidsms.contrib.locations.models import Location
from rapidsms_xforms.models import XFormSubmission
from poll.models import Response
import datetime
from django.utils.safestring import mark_safe
import calendar
import time
import re

def get_section(path):
    pos = path.split('/')
    return pos[2]

def get_parent(location_id):
    if location_id:
        location = get_object_or_404(Location, pk=location_id)
    else:
        location = Location.tree.root_nodes()[0]
    return location

def get_parentId(location_id):
    if location_id:
        location = get_object_or_404(Location, pk=location_id)
    else:
        location = Location.tree.root_nodes()[0]
    return location.parent_id

def get_ancestors(location_id):
    if location_id:
        location = get_object_or_404(Location, pk=location_id)
    else:
        location = Location.tree.root_nodes()[0]
    return location.get_ancestors()

def get_district(location):
    try:
        return location.get_ancestors().get(type='district').name
    except:
        return location

def name(location):
    return location.name

def latest(obj):
    scripted_polls = ['emis_abuse', 'emis_meals', 'emis_grant', 'emis_inspection', 'emis_cct', 'emis_abuse', 'emis_sms_meals', 'emis_grant_notice', 'emis_inspection_yesno', 'emis_meetings', 'emis_classroom', 'emis_classroom_use', 'emis_latrines', 'emis_latrines_use', 'emis_teachers', 'emis_boys_enrolled', 'emis_girls_enrolled']
    try:
        responses = Response.objects.filter(poll__name__in=scripted_polls, message__connection__in=obj.connection_set.all())
        poll_date = responses.latest('date').date
    except:
        poll_date = datetime.datetime(1900, 1, 1)
    try:
        xform_date = XFormSubmission.objects.filter(connection__in=obj.connection_set.all()).latest('created').created
    except:
        xform_date = datetime.datetime(1900, 1, 1)

    if poll_date > xform_date:
        return poll_date
    elif xform_date > poll_date:
        return xform_date
    else:
        return None
    
def submissions(obj):
    scripted_polls = ['emis_abuse', 'emis_meals', 'emis_grant', 'emis_inspection', 'emis_cct', 'emis_abuse', 'emis_sms_meals', 'emis_grant_notice', 'emis_inspection_yesno', 'emis_meetings', 'emis_classroom', 'emis_classroom_use', 'emis_latrines', 'emis_latrines_use', 'emis_teachers', 'emis_boys_enrolled', 'emis_girls_enrolled']
    try:
        resp_count = Response.objects.filter(poll__name__in=scripted_polls, message__connection__in=obj.connection_set.all()).count()
    except:
        resp_count = 0
    try:
        subs_count = XFormSubmission.objects.filter(connection__in=obj.connection_set.all()).count()
    except:
        subs_count = 0
    return resp_count + subs_count

def headteacher(obj):
    try:
        reps = obj.emisreporter_set.filter(groups__name='Head Teachers')
        return reps[0].name
    except:
        return ''
    
def headteacher_connection(obj):
    try:
        reps = obj.emisreporter_set.filter(groups__name='Head Teachers')
        return reps[0].default_connection.identity
    except:
        return ''

def hash(h, key):
    try:
        val = h[key]
    except KeyError:
        val = None
    return val
month_options = (
    (),
    (1, 'Jan'),
    (2, 'Feb'),
    (3, 'Mar'),
    (4, 'Apr'),
    (5, 'May'),
    (6, 'Jun'),
    (7, 'Jul'),
    (8, 'Aug'),
    (9, 'Sept'),
    (10, 'Oct'),
    (11, 'Nov'),
    (12, 'Dec'),
)

class DateRangeNode(template.Node):

    def __init__(self , min_date, max_date, start_date, end_date):
        self.end_date = template.Variable(end_date)
        self.start_date = template.Variable(start_date)
        self.min_date = template.Variable(min_date)
        self.max_date = template.Variable(max_date)
    def render(self, context):
        try:
            end_date = self.end_date.resolve(context)
            start_date = self.start_date.resolve(context)
            min_date = self.min_date.resolve(context)
            max_date = self.max_date.resolve(context)
        except template.VariableDoesNotExist:
            return ''
        start_date = datetime.datetime.fromtimestamp(start_date / 1000)
        end_date = datetime.datetime.fromtimestamp(end_date / 1000)
        min_date = datetime.datetime.fromtimestamp(min_date / 1000)
        max_date = datetime.datetime.fromtimestamp(max_date / 1000)

        years = range(min_date.year, max_date.year + 1)
        start_opts = \
        """
            <label for='%s'>%s</label>
            <select name='%s' id='%s' style='display:none;'>"""
        for year in years:

            opt_year = "<optgroup label='%s'>" % str(year)
            start_opts = start_opts + opt_year
            if year == min_date.year:
                for month in range(min_date.month, 13):
                    opt_month = "<optgroup label='%s'>" % str(month_options[month][1])
                    start_opts = start_opts + opt_month
                    for day in range(1, calendar.monthrange(year, month)[1] + 1):
                        option = "<option value=%d>%s-%s-%s</option>"\
                     % (time.mktime(datetime.datetime(year, month, day).timetuple()) * 1000, str(day), str(month_options[month][1]), str(year))
                        start_opts = start_opts + option
                    start_opts = start_opts + '</optgroup>'


            elif year == max_date.year:
                for month in range(1, max_date.month + 1):
                    opt_month = "<optgroup label='%s'>" % str(month_options[month][1])
                    start_opts = start_opts + opt_month
                    for day in range(1, calendar.monthrange(year, month)[1] + 1):
                        option = "<option value=%d>%s-%s-%s</option>"\
                     % (time.mktime(datetime.datetime(year, month, day).timetuple()) * 1000, str(day), str(month_options[month][1]), str(year))
                        start_opts = start_opts + option
                    start_opts = start_opts + '</optgroup>'
            else:
                for month in range(1, 13):
                    opt_month = "<optgroup label='%s'>" % str(month_options[month][1])
                    start_opts = start_opts + opt_month
                    for day in range(1, calendar.monthrange(year, month)[1] + 1):
                        option = "<option value=%d>%s-%s-%s</option>"\
                     % (time.mktime(datetime.datetime(year, month, day).timetuple()) * 1000, str(day), str(month_options[month][1]), str(year))
                        start_opts = start_opts + option
                    start_opts = start_opts + '</optgroup>'

            start_opts = start_opts + '</optgroup>'
        start_opts = start_opts + '</select>'
        start_ts = time.mktime(start_date.date().timetuple()) * 1000
        end_ts = time.mktime(end_date.date().timetuple()) * 1000
        start_re = re.compile("<option value=%d>" % start_ts)
        end_re = re.compile("<option value=%d>" % end_ts)
        start_selected_str = "<option value=%d' selected='selected'>" % start_ts
        end_selected_str = "<option value=%d' selected='selected'>" % end_ts
        start_html = start_opts % ('start', '', 'start', 'start')
        end_html = start_opts % ('end', '', 'end', 'end')
        start_html = start_re.sub(start_selected_str, start_html)
        end_html = end_re.sub(end_selected_str, end_html)
        return mark_safe(start_html + end_html)




def do_date_range(parser, token):
	"""
	returns dateranges grouped by month and by week

	"""
	chunks = token.split_contents()
	if not len(chunks) == 5:
		raise template.TemplateSyntaxError, "%r tag requires two arguments" % token.contents.split()[0]

	return DateRangeNode(chunks[1], chunks[2], chunks[3], chunks[4])

def distinct_connections(obj):
    connections = []
    if obj.connection_set.count() > 1:
        for c in obj.connection_set.all():
            if c.backend.name =='yo6200':
                connections.append(c)
    else:
        connections.append(obj.connection_set.all()[0])
    return connections

def last_report(obj, alert):
    if alert == "1":
        keywords = ["boys", "girls"]
    elif alert == "2":
        keywords = ["enrolledb", "enrolledg"]
    else:
        keywords = ["deploy"]
    try:
        reporter_connections = []
        q = Q(xform__keyword__icontains=keywords[0])
        for w in keywords[1:]:  
            q = q | Q(xform__keyword__icontains=w)
        for reporter in obj.emisreporter_set.all():
            for c in reporter.connection_set.all():
                reporter_connections.append(c)
        xform_date = XFormSubmission.objects.filter(connection__in=reporter_connections)\
                    .filter(q)\
                    .latest('created').created
    except:
        xform_date = None

    return xform_date      


def parse_gemvalues(obj):
    if obj.value_text:
        return obj.value_text
    elif obj.value_int == 0:
        return 'No'
    else:
        return 'Yes'
    
def reorganize_lunch(obj):
    lunches = []
    print obj
    for label, lunch in obj:
        lunches.append("%s-%d"%(label,lunch))
    return lunches
register = template.Library()
register.filter('section', get_section)
register.filter('parent', get_parent)
register.filter('parentId', get_parentId)
register.filter('ancestors', get_ancestors)
register.filter('name', name)
register.filter('latest', latest)
register.filter('distinct_connections', distinct_connections)
register.filter('last_report', last_report)
register.filter('submissions', submissions)
register.filter('headteacher',headteacher)
register.filter('parse_gemvalues', parse_gemvalues)
register.filter('reorganize_lunch', reorganize_lunch)
register.filter('headteacher_connection',headteacher_connection)
register.filter('hash', hash)
register.filter('get_district', get_district)
register.tag('date_range', do_date_range)
