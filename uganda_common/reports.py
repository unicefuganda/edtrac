from generic.reports import Report
from generic.reporting.reports import Column
from .utils import total_submissions, reorganize_location, total_attribute_value
from rapidsms.contrib.locations.models import Location
from generic.reporting.views import BasicDateGetter
from generic.reporting.forms import DateRangeForm
from django.db import connection
import datetime

class XFormDateGetter(BasicDateGetter):
    def get_dates(self, request):
        """
        Process date variables from POST, session, or defaults
        """
        if request.POST:
            form = DateRangeForm(request.POST)
            if form.is_valid():
                cursor = connection.cursor()
                cursor.execute("select min(created) from rapidsms_xforms_xformsubmission")
                min_date = cursor.fetchone()[0] or (datetime.datetime.now() - datetime.timedelta(365))
                start_date = form.cleaned_data['start']
                end_date = form.cleaned_data['end']
                request.session['start_date'] = start_date
                request.session['end_date'] = end_date
                return {
                    'max':datetime.datetime.now(),
                    'min':min_date,
                    'start':start_date,
                    'end':end_date,
                }
            else:
                return {}
        else:
            cursor = connection.cursor()
            cursor.execute("select min(created), max(created) from rapidsms_xforms_xformsubmission")
            min_date, end_date = cursor.fetchone()
            end_date = end_date or datetime.datetime.now()
            min_date = min_date or (datetime.datetime.now() - datetime.timedelta(365))
            start_date = end_date - datetime.timedelta(days=30)
            if request.session.get('start_date', None)  and request.session.get('end_date', None):
                start_date = request.session['start_date']
                end_date = request.session['end_date']

            return {
                'max':datetime.datetime.now(),
                'min':min_date,
                'start':start_date,
                'end':end_date,
            }


class QuotientColumn(Column):
    def __init__(self, top_column, bottom_column, **kwargs):
        Column.__init__(self, **kwargs)
        self.top_column = top_column
        self.bottom_column = bottom_column
        self.chart_yaxis = 'Percentage of Reports'
        if not self.chart_title:
            self.chart_title = 'Variation of %s' % self.get_title()


    def set_report(self, report):
        Column.set_report(self, report)
        self.top_column.set_report(report)
        self.bottom_column.set_report(report)


    def add_to_report(self, report, key, dictionary):
        temp = {}
        self.top_column.add_to_report(report, 'top', temp)
        self.bottom_column.add_to_report(report, 'bottom', temp)
        for row_key, items in temp.items():
            if 'bottom' in items:
                bottom = items['bottom']
                top = items.setdefault('top', 0)
                quotient = round(((float(top) / bottom) * 100), 1)
                dictionary.setdefault(row_key, {'location_name':items['location_name']})
                dictionary[row_key][key] = quotient


    def get_chart(self):
        from .views import PercentageChartView
        return PercentageChartView(location_id=self.report.location.pk, \
                         start_date=self.report.start_date, \
                         end_date=self.report.end_date, \
                         top_column=self.top_column, \
                         bottom_column=self.bottom_column,
                         chart_title=self.chart_title,
                         chart_subtitle=self.chart_subtitle,
                         chart_yaxis=self.chart_yaxis)

    def get_view_function(self):
        from .views import PercentageChartView
        return PercentageChartView.as_view(location_id=self.report.location.pk, \
                         start_date=self.report.start_date, \
                         end_date=self.report.end_date, \
                         top_column=self.top_column, \
                         bottom_column=self.bottom_column,
                         chart_title=self.chart_title,
                         chart_subtitle=self.chart_subtitle,
                         chart_yaxis=self.chart_yaxis)


class XFormSubmissionColumn(Column):
    def __init__(self, keyword, extra_filters=None, **kwargs):
        Column.__init__(self, **kwargs)
        self.keyword = keyword
        self.extra_filters = extra_filters
        self.chart_yaxis = 'Number of Reports'
        if not self.chart_title:
            self.chart_title = 'Variation of %s' % self.get_title()

    def add_to_report(self, report, key, dictionary):
        val = total_submissions(self.keyword, report.start_date, report.end_date, report.location, self.extra_filters)
        reorganize_location(key, val, dictionary)

    def get_chart(self):
        from .views import XFormChartView
        return XFormChartView(location_id=self.report.location.pk, \
                         start_date=self.report.start_date, \
                         end_date=self.report.end_date, \
                         xform_keyword=self.keyword,
                         extra_filters=self.extra_filters,
                         chart_title=self.chart_title,
                         chart_subtitle=self.chart_subtitle,
                         chart_yaxis=self.chart_yaxis)

    def get_view_function(self):
        from .views import XFormChartView
        return XFormChartView.as_view(location_id=self.report.location.pk, \
                         start_date=self.report.start_date, \
                         end_date=self.report.end_date, \
                         xform_keyword=self.keyword,
                         extra_filters=self.extra_filters,
                         chart_title=self.chart_title,
                         chart_subtitle=self.chart_subtitle,
                         chart_yaxis=self.chart_yaxis)


class XFormAttributeColumn(Column):
    def __init__(self, keyword, extra_filters=None, **kwargs):
        Column.__init__(self, **kwargs)
        self.keyword = keyword
        s = self.keyword.split('_')
        self.xform_keyword = s[0]
        self.attribute_keyword = s[1]
        self.extra_filters = extra_filters
        self.chart_yaxis = 'Number of Reports'
        if not self.chart_title:
            self.chart_title = 'Variation of %s' % self.get_title()

    def add_to_report(self, report, key, dictionary):
        val = total_attribute_value(self.keyword, report.start_date, report.end_date, report.location, self.extra_filters)
        reorganize_location(key, val, dictionary)

    def get_chart(self):
        from .views import XFormChartView
        return XFormChartView(location_id=self.report.location.pk, \
                         start_date=self.report.start_date, \
                         end_date=self.report.end_date, \
                         xform_keyword=self.xform_keyword,
                         attribute_keyword=self.attribute_keyword,
                         extra_filters=self.extra_filters,
                         chart_title=self.chart_title,
                         chart_subtitle=self.chart_subtitle,
                         chart_yaxis=self.chart_yaxis)

    def get_view_function(self):
        from .views import XFormChartView
        return XFormChartView.as_view(location_id=self.report.location.pk, \
                         start_date=self.report.start_date, \
                         end_date=self.report.end_date, \
                         xform_keyword=self.xform_keyword,
                         attribute_keyword=self.attribute_keyword,
                         extra_filters=self.extra_filters,
                         chart_title=self.chart_title,
                         chart_subtitle=self.chart_subtitle,
                         chart_yaxis=self.chart_yaxis)


class PollNumericResultsColumn(Column):

    AVERAGE = 1
    MAX = 2
    MIN = 4
    COUNT = 8
    STDDEV = 16
    SUM = 32

    VALUE_FLAGS = [(AVERAGE, 'avg'),
                   (MAX, 'max'),
                   (MIN, 'min'),
                   (COUNT, 'count'),
                   (STDDEV, 'stddev'),
                   (SUM, 'sum')]

    def __init__(self, poll_name, attrs=SUM):
        self.poll = Poll.objects.get(name=poll_name)
        self.attrs = attrs

    def add_to_report(self, report, key, dictionary):
        var = poll.get_numeric_report_data(location=report.location)
        for dict in var:
            loc_id = dict['location_id']
            dictionary.setdefault(loc_id, {'location_name':dict['location_name'], 'diff':(dict['rght'] - dict['lft'])})
            report.columns = report.columns[0:len(report._columns) - 1]
            for flag, attrkey in VALUE_FLAGS:
                if self.attrs & flag:
                    dictionary[loc_name]["%s_%s" % (key, attrkey)] = dict["value_float__%s" % attrkey]
                    report.columns.append("%s_%s" % (key, attrkey))


class PollCategoryResultsColumn(Column):

    def __init__(self, poll, category):
        self.poll = Poll.obects.get(name=poll_name)
        self.category = Category.objects.get(poll=self.poll, name=category)

    def add_to_report(self, report, key, dictionary):
        var = poll.responses_by_category(location=report.location)
        if len(var):
            location_id = var[0]['location_id']
            total = 0
            category_dict = {}
            for dict in var:
                if dict['location_id'] == location_id:
                    dictionary.setdefault(location_id, {'location_name':dict['location_name'], 'diff':(dict['rght'] - dict['lft'])})
                    category_dict[dict['category__name']] = dict['value']
                    total = total + dict['value']
                else:
                    dictionary[location_id][key] = (category_dict[self.category] if self.category.name in category_dict else 0) / total
                    location_id = dict['location_id']
                    dictionary.setdefault(location_id, {'location_name':dict['location_name'], 'diff':(dict['rght'] - dict['lft'])})
                    category_dict = {}
                    category_dict[dict['category__name']] = dict['value']
                    total = dict['value']
            dictionary[location_id][key] = (category_dict[self.category] if self.category.name in category_dict else 0) / total


class LocationReport(Report):
    def __init__(self, request, dates):
        try:
            self.location = Location.objects.get(pk=int(request.POST['drill_key']))
        except:
            self.location = Location.tree.root_nodes()[0]
        Report.__init__(self, request, dates)
