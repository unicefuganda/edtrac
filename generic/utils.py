from .models import *
from .forms import DateRangeForm
import datetime, time
from django.core.paginator import Paginator, InvalidPage, EmptyPage


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


def paginate(filtered_list,objects_per_page,page,p):
    if hasattr(filtered_list, 'count') and callable(filtered_list.count):
        try:
            total = filtered_list.count()
        except TypeError:
            total = len(filtered_list)
    else:
        total = len(filtered_list)
    ranges = []
    paginator = Paginator(filtered_list, objects_per_page)
    if p and p <= paginator.num_pages:
        page=p
        # If page request is out of range, deliver last page of results.
    try:
        filtered_list = paginator.page(page).object_list
    except (EmptyPage, InvalidPage):
        filtered_list = paginator.page(paginator.num_pages).object_list
        page = paginator.num_pages
    if paginator.num_pages > 10:
        low_range = range(1, 6)
        high_range = range(paginator.num_pages - 4, paginator.num_pages + 1)
        if page < 10:
            low_range += range(6, min(paginator.num_pages, page + 5))
            mid_range = range(10, paginator.num_pages - 10, 10)
            ranges.append(low_range)
            ranges.append(mid_range)
            ranges.append(high_range)
        elif page > paginator.num_pages - 10:
            high_range = range(max(0, page - 5), paginator.num_pages - 4) + high_range
            mid_range = range(10, paginator.num_pages - 10, 10)
            ranges.append(low_range)
            ranges.append(mid_range)
            ranges.append(high_range)
        else:
            ranges.append(low_range)
            ranges.append(range(10, max(0, page - 2), 10))
            ranges.append(range(max(0, page - 2), min(paginator.num_pages, page + 3)))
            ranges.append(range(int(round(min(paginator.num_pages, page + 3) / 10) + 1) * 10, paginator.num_pages - 10, 10))
            ranges.append(high_range)

    else:
        ranges.append(paginator.page_range)

    return dict(total=total,ranges=ranges,paginator=paginator,object_list=filtered_list,page=page)


