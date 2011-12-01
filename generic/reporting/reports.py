import datetime, time
from generic.reporting.forms import DateRangeForm

class Column(object):
    report = None
    order = 0
    title = None
    chart_title = None
    chart_subtitle = None
    chart_yaxis = None

    def get_title(self):
        return self.title

    def set_report(self, report):
        self.report = report

    def add_to_report(self, report, key, dictionary):
        pass

    def get_chart(self):
        return None

    def get_redirect(self):
        None

    def get_view_function(self):
        return None

    def get_order(self):
        return self.order

    def __init__(self, order=0, title=None, chart_title=None, chart_subtitle=None, chart_yaxis=None):
        self.order = order
        self.title = title
        self.chart_title = chart_title
        self.chart_subtitle = chart_subtitle
        self.chart_yaxis = chart_yaxis


class BasicDateGetter(object):
    def get_dates(self, request):
        to_ret = {}
        if self.request.POST:
            form = DateRangeForm(self.request.POST)
            if form.is_valid():
                to_ret['start'] = form.cleaned_data['start']
                to_ret['end'] = form.cleaned_data['end']
        return to_ret

    def set_default_dates(self, request, context):
        dates = self.get_dates(request)
        max_date = dates.setdefault('max', datetime.datetime.now())
        min_date = dates.setdefault('min', max_date - datetime.timedelta(days=365))
        min_date = datetime.datetime(min_date.year, min_date.month, 1)
        max_date = datetime.datetime(max_date.year, max_date.month, 1) + datetime.timedelta(days=30)
        start_date = dates.setdefault('start', min_date)
        start_date = datetime.datetime(start_date.year, start_date.month, start_date.day)
        end_date = dates.setdefault('end', max_date)
        end_date = datetime.datetime(end_date.year, end_date.month, end_date.day)
        max_ts = time.mktime(max_date.timetuple())
        min_ts = time.mktime(min_date.timetuple())
        start_ts = time.mktime(start_date.timetuple())
        end_ts = time.mktime(end_date.timetuple())

        context.update({
            'max_ts':max_ts, \
            'min_ts':min_ts, \
            'selected_ts':[(start_ts, 'start',), (end_ts, 'end',)],
            'start_ts':start_ts,
            'end_ts':end_ts,
            'start_date':start_date,
            'end_date':end_date,
            'ts_range':range(long(min_ts), long(max_ts) + 1, 86400), \
        })

    def add_dates_to_context(self, request, context):
        self.set_default_dates(request, context)
