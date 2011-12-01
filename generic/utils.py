from .models import *
from .forms import DateRangeForm
import datetime, time


def copy_dashboard(from_dashboard, to_dashboard):
    for m in to_dashboard.modules.all():
        m.delete()
    for mod_obj in from_dashboard.modules.all():
        mod = to_dashboard.modules.create(title=mod_obj.title,
                                       view_name=mod_obj.view_name,
                                       column=mod_obj.column,
                                       offset=mod_obj.offset)
        mod.save()
        for param in mod_obj.params.all():
            mod_params = mod.params.create(param_name=param.param_name,
                                           param_value=param.param_value,
                                           is_url_param=param.is_url_param)
            mod_params.save()


def get_dates(request):
    to_ret = {}
    if request.POST:
        form = DateRangeForm(request.POST)
        if form.is_valid():
            to_ret['start'] = form.cleaned_data['start']
            to_ret['end'] = form.cleaned_data['end']
    return to_ret


def set_default_dates(dates, request, context):
    if callable(dates):
        dates = dates(request=request)
    max_date = dates.setdefault('max', datetime.datetime.now())
    min_date = dates.setdefault('min', max_date - datetime.timedelta(days=365))
    min_date = datetime.datetime(min_date.year, min_date.month, 1)
    max_date = datetime.datetime(max_date.year, max_date.month, 1) + datetime.timedelta(days=30)
    start_date = dates.setdefault('start', min_date)
    start_date = datetime.datetime(start_date.year, start_date.month, start_date.day)
    end_date = dates.setdefault('end', min_date)
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


def flatten_list(report_dict):
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
