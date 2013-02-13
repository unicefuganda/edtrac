from django.views.generic.base import TemplateView, View, TemplateResponseMixin
from .reports import Column, BasicDateGetter
from rapidsms.contrib.locations.models import Location
import datetime, time
from django.shortcuts import get_object_or_404
from django.utils import simplejson
from django.http import HttpResponse
from django.conf.urls.defaults import *

GROUP_BY_WEEK = 1
GROUP_BY_MONTH = 2
GROUP_BY_DAY = 16
GROUP_BY_QUARTER = 32

class JsonResponse(HttpResponse):
    """ return json content type   """

    def __init__(self, obj):
        self.original_obj = obj
        HttpResponse.__init__(self, self.serialize())
        self['Content-Type'] = 'text/javascript'

    def serialize(self):
        return simplejson.dumps(self.original_obj)


class ChartView(View):
    http_method_names = ['post']
    start_date = None
    end_date = None
    date_getter = BasicDateGetter()
    chart_title = None
    chart_subtitle = None
    chart_yaxis = 'Value'

    def as_url(self):
        return ''

    def get_chart_title(self):
        return self.chart_title

    def get_chart_subtitle(self):
        return self.chart_subtitle or \
            "From %s to %s" % (self.start_date.strftime("%Y-%m-%d"), \
                               self.end_date.strftime("%Y-%m-%d"))

    def get_y_axis(self):
        return self.chart_yaxis

    def get_group_by(self, start_date, end_date):
        # The two if statements that follow are just for cases where start_date and end-date are missing
        if not end_date:
            end_date = datetime.datetime.now() - datetime.timedelta(days=13)
            end_date = datetime.datetime(end_date.year, end_date.month, end_date.day)
        if not start_date:
            start_date = end_date - datetime.timedelta(days=79)
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

    def get_data(self):
        group_by = self.get_group_by(self.start_date, self.end_date)

        json_response_data = {'series':[{'name':'apples', 'data':[[0, 1], [1, 2][2, 3]]}], \
                              'timespan':group_by['group_by_name'], \
                              'title':self.get_chart_title(), \
                              'subtitle':self.get_chart_subtitle(), \
                              'yaxis':self.get_y_axis(), \
                              }
        return json_response_data

    def drill_on(self, key):
        pass

    def render_to_response(self, context):
        if self.request.method == 'POST':
            if 'drill_key' in self.request.POST and self.request.POST['drill_key']:
                self.drill_on(self.request.POST['drill_key'])

        self.date_getter.add_dates_to_context(self.request, context)
        self.start_date = context['start_date']
        self.end_date = context['end_date']

        json_response_data = self.get_data()
        return JsonResponse(json_response_data)

    def add_data_to_context(self, context):
        json_response_data = self.get_data()
        context['chart'] = json_response_data

    def post(self, request, *args, **kwargs):
        return self.render_to_response({})


class ReportView(View, TemplateResponseMixin):
    http_method_names = ['get', 'post']
    template_name = "generic/reporting/report_base.html"
    partial_base = "generic/reporting/partials/partial_base.html"
    partial_row = "generic/reporting/partials/partial_row.html"
    drill_key = "key"
    row_name_key = "location_name"
    needs_date = True
    date_getter = BasicDateGetter()
    has_chart = True
    start_date = None
    end_date = None

    def get(self, request, *args, **kwargs):
        return self.render_to_response({})

    def post(self, request, *args, **kwargs):
        return self.render_to_response({})

    def __init__(self):
        self.columns = self.get_columns()
        self.top_columns = self.get_top_columns()
        self.location = Location.tree.root_nodes()[0]

        for colname, column in self.columns:
            column.set_report(self)

    def get_top_columns(self):
        return []

    def get_columns(self):
        toret = []
        for attrname in dir(self):
            try:
                val = getattr(self, attrname)
                if issubclass(type(val), Column):
                    toret.append((attrname, val,))
            except AttributeError:
                continue
        toret = sorted(toret, key=lambda column: column[1].get_order())
        return toret

    def get_default_column(self):
        return self.columns[0]

    def flatten_list(self, report_dict):
        """
            Rearrange a dictionary of dictionaries:
                { 'apple':{'a':1,'b':2,'c':3},
                  'orange':{'d':4,'e':5,'f':6} }
                  
            Into a list of dictionaries:
               [{'key':'apple','a':1,'b':2,'c':3},{'key':'orange','d':4,'e':5,'f':6}]
        """
        toret = []
        for key, value_dict in report_dict.items():
            value_dict['key'] = key
            toret.append(value_dict)
        return toret

    def compile_report(self):
        toret = {}
        for attrname, colinstance in self.columns:
            colinstance.add_to_report(self, attrname, toret)

        return self.flatten_list(toret)

    def drill_on(self, key):
        try:
            self.location = Location.objects.get(pk=key)
        except Location.DoesNotExist:
            self.location = Location.tree.root_nodes()[0]

    def render_to_response(self, context):
        if self.needs_date:
            self.date_getter.add_dates_to_context(self.request, context)
            context['timeslider_update'] = 'filter_report(this)'

        self.start_date = context['start_date']
        self.end_date = context['end_date']

        if self.request.method == 'POST':
            self.template_name = self.partial_base
            if 'drill_key' in self.request.POST and self.request.POST['drill_key']:
                self.drill_on(self.request.POST['drill_key'])

        self.report = self.compile_report()

        chart_url = '#'
        if self.has_chart:
            self.get_default_column()[1].get_chart().add_data_to_context(context)
            chart_url = "column/%s/" % self.get_default_column()[0]

        context.update({\
            'report':self.report, \
            'columns':self.columns, \
            'top_columns':self.top_columns, \
            'partial_base':self.partial_base, \
            'partial_row':self.partial_row, \
            'drill_key':self.drill_key, \
            'row_name_key':self.row_name_key, \
            'needs_date':self.needs_date, \
            'has_chart':self.has_chart, \
            'chart_url':chart_url, \
            'location':self.location, \
            'module':False})
        return super(ReportView, self).render_to_response(context)

    def as_urlpatterns(self, name=None,login_wrapper=None):
        """
        Creates the appropriate URL patterns for this object.
        The root url (to the main report page) can take an optional 'name'
        parameter.
        """
        urlpatterns = patterns('')
        if name:
            if login_wrapper:
                urlpatterns += patterns('', url(r'^$', login_wrapper(self.__class__.as_view()), name=name))
            else:
                urlpatterns += patterns('', url(r'^$', self.__class__.as_view(), name=name))
        else:
            if login_wrapper:
                urlpatterns += patterns('', url(r'^$', login_wrapper(self.__class__.as_view())))
            else:
                urlpatterns += patterns('', (r'^$', self.__class__.as_view()))

        for attname, column in self.columns:
            v = column.get_view_function()
            if v:
                urlpatterns += patterns('', (r'^column/%s/$' % attname.lower(), v))

        return urlpatterns


