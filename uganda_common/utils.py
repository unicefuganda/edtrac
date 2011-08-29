from django.conf import settings, settings
from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.db.models.base import ModelBase
from django.db.models.query import QuerySet, ValuesQuerySet
from django.http import HttpResponse
from django.utils.text import capfirst
from eav.models import Attribute
from poll.models import Poll, LocationResponseForm, \
    STARTSWITH_PATTERN_TEMPLATE
from rapidsms.contrib.locations.models import Location
from rapidsms.models import Backend
from rapidsms_xforms.models import XForm, XFormField, XFormFieldConstraint, \
    XFormSubmission, XFormSubmissionValue
from script.models import Script, ScriptStep
import datetime
import difflib
import re
import traceback
from .forms import DateRangeForm
from django.db.models import Max, Min

def previous_calendar_week():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    return (start_date, end_date)


def previous_calendar_month():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)
    return (start_date, end_date)


def previous_calendar_quarter():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=90)
    return (start_date, end_date)

TIME_RANGES = {
    'w': previous_calendar_week,
    'm': previous_calendar_month,
    'q': previous_calendar_quarter

}

def assign_backend(number):
    """assign a backend to a given number"""
    country_code = getattr(settings, 'COUNTRY_CALLING_CODE', '256')
    backends = getattr(settings, 'BACKEND_PREFIXES', [('70', 'warid'), ('75', 'zain'), ('71', 'utl'), ('', 'dmark')])

    if number.startswith('0'):
        number = '%s%s' % (country_code, number[1:])
    elif number[:len(country_code)] != country_code:
        number = '%s%s' % (country_code, number)
    backendobj = None
    for prefix, backend in backends:
        if number[len(country_code):].startswith(prefix):
            backendobj, created = Backend.objects.get_or_create(name=backend)
            break
    return (number, backendobj)

class ExcelResponse(HttpResponse):
    def __init__(self, data, output_name='excel_report', headers=None, write_to_file=False,force_csv=False, encoding='utf8'):
        # Make sure we've got the right type of data to work with
        valid_data = False
        if hasattr(data, '__getitem__'):
            if isinstance(data[0], dict):
                if headers is None:
                    headers = data[0].keys()
                data = [[row[col] for col in headers] for row in data]
                data.insert(0, headers)
            if hasattr(data[0], '__getitem__'):
                valid_data = True
        import StringIO
        output = StringIO.StringIO()
        # Excel has a limit on number of rows; if we have more than that, make a csv
        use_xls = False
        if len(data) <= 65536 and force_csv is not True:
            try:
                import xlwt
            except ImportError:
                # xlwt doesn't exist; fall back to csv
                pass
            else:
                use_xls = True
        if use_xls:
            ##formatting of the cells
            # Grey background for the header row
            BkgPat = xlwt.Pattern()
            BkgPat.pattern = xlwt.Pattern.SOLID_PATTERN
            BkgPat.pattern_fore_colour = 22

            # Bold Fonts for the header row
            font = xlwt.Font()
            font.name = 'Calibri'
            font.bold = True

            # Non-Bold fonts for the body
            font0 = xlwt.Font()
            font0.name = 'Calibri'
            font0.bold = False

            # style and write field labels
            style = xlwt.XFStyle()
            style.font = font
            style.pattern = BkgPat

            style0 = xlwt.XFStyle()
            style0.font = font0
            book = xlwt.Workbook(encoding=encoding)
            sheet = book.add_sheet('Sheet 1')
            styles = {'datetime': xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
                      'date': xlwt.easyxf(num_format_str='yyyy-mm-dd'),
                      'time': xlwt.easyxf(num_format_str='hh:mm:ss'),
                      'default': style0,
                      'header':style}

            for rowx, row in enumerate(data):
                for colx, value in enumerate(row):
                    if isinstance(value, datetime.datetime):
                        cell_style = styles['datetime']
                    elif isinstance(value, datetime.date):
                        cell_style = styles['date']
                    elif isinstance(value, datetime.time):
                        cell_style = styles['time']
                    elif rowx == 0:
                        cell_style = styles['header']
                    else:
                        cell_style = styles['default']

                    sheet.write(rowx, colx, value, style=cell_style)
            if write_to_file:
                book.save(output_name)
            book.save(output)
            mimetype = 'application/vnd.ms-excel'
            file_ext = 'xls'
        else:
            for row in data:
                out_row = []
                for value in row:
                    if not isinstance(value, basestring):
                        value = unicode(value)
                    value = value.encode(encoding)
                    out_row.append(value.replace('"', '""'))
                output.write('"%s"\n' %
                             '","'.join(out_row))
            mimetype = 'text/csv'
            file_ext = 'csv'
        output.seek(0)
        super(ExcelResponse, self).__init__(content=output.getvalue(),
                                            mimetype=mimetype)

        self['Content-Disposition'] = 'attachment;filename="%s.%s"' % \
            (output_name.replace('"', '\"'), file_ext)

def parse_district_value(value):
    location_template = STARTSWITH_PATTERN_TEMPLATE % '[a-zA-Z]*'
    regex = re.compile(location_template)
    toret = find_closest_match(value, Location.objects.filter(type__name='district'))
    if not toret:
        raise ValidationError("We didn't recognize your district.  Please carefully type the name of your district and re-send.")
    else:
        return toret

Poll.register_poll_type('district', 'District Response', parse_district_value, db_type=Attribute.TYPE_OBJECT, \
                        view_template='polls/response_location_view.html',
                        edit_template='polls/response_location_edit.html',
                        report_columns=(('Text', 'text'), ('Location', 'location'), ('Categories', 'categories')),
                        edit_form=LocationResponseForm)



GROUP_BY_WEEK = 1
GROUP_BY_MONTH = 2
GROUP_BY_DAY = 16
GROUP_BY_QUARTER = 32

months = {
    1: 'Jan',
    2: 'Feb',
    3: 'Mar',
    4: 'Apr',
    5: 'May',
    6: 'Jun',
    7: 'Jul',
    8: 'Aug',
    9: 'Sept',
    10: 'Oct',
    11: 'Nov',
    12: 'Dec'
}

quarters = {
    1:'First',
    2:'Second',
    3:'Third',
    4:'Forth'
}

GROUP_BY_SELECTS = {
    GROUP_BY_DAY:('day', 'date(rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_WEEK:('week', 'extract(week from rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_MONTH:('month', 'extract(month from rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_QUARTER:('quarter', 'extract(quarter from rapidsms_xforms_xformsubmission.created)',),
}


def total_submissions(keyword, start_date, end_date, location, extra_filters=None, group_by_timespan=None):
    if extra_filters:
        extra_filters = dict([(str(k), v) for k, v in extra_filters.items()])
        q = XFormSubmission.objects.filter(**extra_filters)
        tnum = 8
    else:
        q = XFormSubmission.objects
        tnum = 6
    select = {
        'location_name':'T%d.name' % tnum,
        'location_id':'T%d.id' % tnum,
        'rght':'T%d.rght' % tnum,
        'lft':'T%d.lft' % tnum,
    }

    values = ['location_name', 'location_id', 'lft', 'rght']
    if group_by_timespan:
         select_value = GROUP_BY_SELECTS[group_by_timespan][0]
         select_clause = GROUP_BY_SELECTS[group_by_timespan][1]
         select.update({select_value:select_clause,
                        'year':'extract (year from rapidsms_xforms_xformsubmission.created)', })
         values.extend([select_value, 'year'])
    if location.get_children().count() > 1:
        location_children_where = 'T%d.id in %s' % (tnum, (str(tuple(location.get_children().values_list(\
                       'pk', flat=True)))))
    else:
        location_children_where = 'T%d.id = %d' % (tnum, location.get_children()[0].pk)

    return q.filter(
               xform__keyword=keyword,
               has_errors=False,
               created__lte=end_date,
               created__gte=start_date).values(
               'connection__contact__reporting_location__name').extra(
               tables=['locations_location'],
               where=[\
                   'T%d.lft <= locations_location.lft' % tnum, \
                   'T%d.rght >= locations_location.rght' % tnum, \
                   location_children_where]).extra(\
               select=select).values(*values).annotate(value=Count('id')).extra(order_by=['location_name'])


def total_attribute_value(attribute_slug, start_date, end_date, location, group_by_timespan=None):
    select = {
        'location_name':'T8.name',
        'location_id':'T8.id',
        'rght':'T8.rght',
        'lft':'T8.lft',
    }
    values = ['location_name', 'location_id', 'lft', 'rght']
    if group_by_timespan:
         select_value = GROUP_BY_SELECTS[group_by_timespan][0]
         select_clause = GROUP_BY_SELECTS[group_by_timespan][1]
         select.update({select_value:select_clause,
                        'year':'extract (year from rapidsms_xforms_xformsubmission.created)', })
         values.extend([select_value, 'year'])
    if location.get_children().count() > 1:
        location_children_where = 'T8.id in %s' % (str(tuple(location.get_children().values_list(\
                       'pk', flat=True))))
    else:
        location_children_where = 'T8.id = %d' % location.get_children()[0].pk
    return XFormSubmissionValue.objects.filter(
               submission__has_errors=False,
               attribute__slug=attribute_slug,
               submission__created__lte=end_date,
               submission__created__gte=start_date).values(
               'submission__connection__contact__reporting_location__name').extra(
               tables=['locations_location'],
               where=[\
                   'T8.lft <= locations_location.lft',
                   'T8.rght >= locations_location.rght',
                   location_children_where]).extra(\
               select=select).values(*values).annotate(value=Sum('value_int')).extra(order_by=['location_name'])


def reorganize_location(key, report, report_dict):
    for dict in report:
        location = dict['location_id']
        report_dict.setdefault(location, {'location_name':dict['location_name'], 'diff':(dict['rght'] - dict['lft'])})
        report_dict[location][key] = dict['value']


def reorganize_timespan(timespan, report, report_dict, location_list, request=None):
    for dict in report:
        time = dict[timespan]
        if timespan == 'month':
            time = datetime.datetime(int(dict['year']), int(time), 1)
        elif timespan == 'week':
            time = datetime.datetime(int(dict['year']), 1, 1) + datetime.timedelta(days=(int(time) * 7))
        elif timespan == 'quarter':
            time = datetime.datetime(int(dict['year']), int(time) * 3, 1)

        report_dict.setdefault(time, {})
        location = dict['location_name']
        report_dict[time][location] = dict['value']

        if not location in location_list:
            location_list.append(location)


def get_group_by(start_date, end_date):
    interval = end_date - start_date
    if interval <= datetime.timedelta(days=21):
        group_by = GROUP_BY_DAY
        prefix = 'day'
    elif datetime.timedelta(days=21) <= interval <= datetime.timedelta(days=90):
        group_by = GROUP_BY_WEEK
        prefix = 'week'
    elif datetime.timedelta(days=90) <= interval <= datetime.timedelta(days=270):
        group_by = GROUP_BY_MONTH
        prefix = 'month'
    else:
        group_by = GROUP_BY_QUARTER
        prefix = 'quarter'
    return {'group_by':group_by, 'group_by_name':prefix}

def get_dates(request):
    """
    Process date variables from POST
    """
    if request.POST:
        form = DateRangeForm(request.POST)
        if form.is_valid():
            dts = XFormSubmission.objects.aggregate(Min('created'))
            min_date = dts['created__min'] or (datetime.datetime.now() - datetime.timedelta(365))
            start_date = form.cleaned_data['start_ts']
            end_date = form.cleaned_data['end_ts']
            request.session['start_date'] = start_date
            request.session['end_date'] = end_date
    #for charts, cached start_date and end_date for charts as one drills down
    elif request.GET.get('start_date', None) and request.GET.get('end_date', None):
        start_date = datetime.datetime.fromtimestamp(int(request.GET['start_date']))
        end_date = datetime.datetime.fromtimestamp(int(request.GET['end_date']))
        request.session['start_date'] = start_date
        request.session['end_date'] = end_date
        return {'start':start_date, 'end':end_date}
    else:
        form = DateRangeForm()
        dts = XFormSubmission.objects.aggregate(Max('created'), Min('created'))
        end_date = dts['created__max'] or datetime.datetime.now()
        min_date = dts['created__min'] or (datetime.datetime.now() - datetime.timedelta(365))
        start_date = end_date - datetime.timedelta(days=30)
        if request.GET.get('date_range', None):
            start_date, end_date = TIME_RANGES[request.GET.get('date_range')]()
            request.session['start_date'], request.session['end_date'] = start_date, end_date
        if request.session.get('start_date', None)  and request.session.get('end_date', None):
            start_date = request.session['start_date']
            end_date = request.session['end_date']

    return {'start':start_date, 'end':end_date, 'min':min_date, 'form':form}

