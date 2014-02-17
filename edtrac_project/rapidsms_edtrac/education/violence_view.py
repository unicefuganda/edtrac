from datetime import datetime
from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib.auth.models import Group
from django.forms import extras
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.safestring import mark_safe
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.core.urlresolvers import reverse

from education.violence_view_helper import get_location_for_violence_view, get_responses_over_depth
from education.models import School, Poll
from education.reports import get_month_day_range
from education.models import EmisReporter
from unregister.models import Blacklist



#@login_required
#def violence_detail(request, district=None):
#    locations = get_location_for_violence_view(district, request)
#    time_range_depth = 2
#    month_range = get_month_day_range(time_range_depth)
#    indicator = "all"
#
#    month_range.reverse()
#    config_list = get_polls_for_keyword(indicator)
#    collective_result, time_data = get_aggregated_report(locations, config_list, month_range)
#    months = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in month_range]
#    return render_to_response('education/admin/detail_violence.html',
#                              {'collective_result_keys': [config['collective_dict_key'] for config in config_list],
#                               'collective_result': collective_result,
#                               'time_data': mark_safe(json.dumps(time_data)),
#                               'months': mark_safe(json.dumps(months)),
#                               "locations": locations},
#                              RequestContext(request))
@login_required
def detailed_violence_view(request, district=None):
    location = get_location_for_violence_view(district, request)
    date_range = get_month_day_range(datetime.now(),depth=datetime.today().month)
    girls_poll = Poll.objects.get(name='edtrac_violence_girls')
    boys_poll = Poll.objects.get(name='edtrac_violence_boys')
    reported_poll = Poll.objects.get(name='edtrac_violence_reported')
    gem_poll = Poll.objects.get(name='edtrac_gem_abuse')
    polls = [girls_poll, boys_poll, reported_poll, gem_poll]
    labels_for_graphs = ['Violence cases agaisnt girls', 'Violence cases against boys', 
                         'Violence cases reported to Police', 'Violence reported by GEM']
    for poll in polls:
        responses = get_responses_over_depth(poll, location, date_range)
    return render_to_response('education/admin/detail_violence.html',
                              {'data_list':zip(responses, labels_for_graphs)}, RequestContext(request))

#@login_required
#def violence_detail_school(request, location):
#    name = request.GET['school']
#    school_id = School.objects.get(name=name, location__name=location).id
#    return redirect(reverse('school-detail',args=(school_id,)))
#
#@login_required()
#def detail_water_view(request,district=None):
#    responses=[]
#    all_data=[]
#    all_categories=[]
#    location = get_location_for_water_view(district,request)
#    water_poll = Poll.objects.get(name='edtrac_water_source')
#    functional_water_poll = Poll.objects.get(name='edtrac_functional_water_source')
#    water_and_soap = Poll.objects.get(name='water_and_soap')
#    polls=[water_poll,functional_water_poll,water_and_soap]
#    labels_for_graphs = ['water source','functional water source','water and soap']
#    for poll in polls:
#        response , monthly_response = get_all_responses(poll,location)
#        categories, data = get_categories_and_data(monthly_response)
#        responses.append(response)
#        all_data.append(data)
#        all_categories.append(categories)
#    return render_to_response('education/admin/detail_water.html',
#                              {'data_list':zip(responses,all_categories,all_data,labels_for_graphs)},
#                              RequestContext(request))
