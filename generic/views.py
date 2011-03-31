from django.db.models.query import RawQuerySet, RawQuerySet
from django.template import RequestContext
from django.shortcuts import redirect, get_object_or_404, render_to_response
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import Http404,HttpResponseServerError,HttpResponseRedirect, HttpResponse
from django import forms
from django.contrib.auth.models import User
from generic.models import Dashboard, Module, ModuleParams
from django.db.models import Count

def generic_row(request, model=None, pk=None, partial_row='generic/partials/partial_row.html', selectable=True):
    if not (model and pk):
        return HttpResponseServerError
    object = get_object_or_404(model, pk=pk)
    return render_to_response(partial_row, {'object':object},
        context_instance=RequestContext(request))

def generic(request,
            model=None,
            queryset=None,
            template_object_name='object_list',
            base_template='generic/base.html',
            partial_base='generic/partials/partial_base.html',
            partial_header='generic/partials/partial_header.html',
            partial_row='generic/partials/partial_row.html',
            paginator_template='generic/partials/pagination.html',
            results_title='Results',
            paginated=True,
            selectable=True,
            objects_per_page=25,
            columns=[('object', False, '')],
            sort_column='',
            sort_ascending=True,
            filter_forms=[],
            action_forms=[],
            **kwargs):

    # model parameter is required
    if not model:
        return HttpResponseServerError

    # querysets can be calls to a function for dynamic, run-time retrieval
    if callable(queryset):
        queryset = queryset()

    # the default list is either a queryset parameter, or all
    # objects from the model parameter
    object_list = queryset or model.objects.all()

    # dynamically create a form class to represent the list of selected results,
    # for performing actions
    class ResultsForm(forms.Form):
        results = forms.ModelMultipleChoiceField(queryset=object_list, widget=forms.CheckboxSelectMultiple())

    class_dict = {}
    action_form_instances = []
    for action_class in action_forms:
        form_instance = action_class()
        fully_qualified_class_name = "%s.%s" % (form_instance.__module__, form_instance.__class__.__name__)
        # we need both a dictionary of action forms (for looking up actions performed)
        # and a list of tuple for rendering within the template in a particular order
        class_dict[fully_qualified_class_name] = action_class
        action_form_instances.append((fully_qualified_class_name,action_class(),))

    filter_form_instances = []
    for filter_class in filter_forms:
        form_instance = filter_class()
        filter_form_instances.append(form_instance)

    # define some defaults
    response_template = base_template
    page = 1
    selected=False
    status_message=''
    status_message_type=''

    if request.method == 'POST':
        page_action = request.POST.get('page_action', '')
        sort_action = request.POST.get('sort_action', '')
        sort_column = request.POST.get('sort_column', '')
        sort_ascending = request.POST.get('sort_ascending', 'True')
        sort_ascending = (sort_ascending == 'True')
        action_taken = request.POST.get('action', '')
        if page_action:
            object_list = request.session['object_list']
            try:
                page = int(request.POST.get('page_num', '1'))
            except ValueError:
                pass
        elif sort_action:
            # retrieve the original, unsorted, unpaginated list,
            # as some sorts will turn the initial queryset into a list
            object_list = request.session['filtered_list']
            for column_name, sortable, sort_param, sorter in columns:
                if sortable and sort_param == sort_column:
                    object_list = sorter.sort(sort_column, object_list, sort_ascending)
        elif action_taken:
            object_list = request.session['object_list']
            everything_selected = request.POST.get('select_everything', None)
            results = []
            if everything_selected:
                results = request.session['object_list']
            else:
                resultsform = ResultsForm(request.POST)
                if resultsform.is_valid():
                    results = resultsform.cleaned_data['results']
            action_class = class_dict[action_taken]
            action_instance = action_class(request.POST)
            if action_instance.is_valid():
                status_message, status_message_type = action_instance.perform(request, results)
        else:
            for form_class in filter_forms:
                form_instance = form_class(request.POST)
                if form_instance.is_valid():
                    object_list = form_instance.filter(request, object_list)
            selected = True
            # store the original, unsorted, unpaginated list,
            # as some sorts will turn the initial queryset into a list
            request.session['filtered_list'] = object_list
        response_template = partial_base
    else:
        # store the full set of models, in queryset form, in the
        # session, for the case of sorting the full list
        request.session['filtered_list'] = object_list

        # calls to this view can define a default sorting order,
        # if it's an initial GET request we should perform this sort here
        if sort_column:
            for column_name, sortable, sort_param, sorter in columns:
                if sortable and sort_param == sort_column:
                    object_list = sorter.sort(sort_column, object_list, sort_ascending)

    request.session['object_list'] = object_list
    total = len(object_list)
    paginator = None
    ranges = []
    if paginated:
        paginator = Paginator(object_list, objects_per_page)
        # If page request is out of range, deliver last page of results.
        try:
            object_list = paginator.page(page).object_list
        except (EmptyPage, InvalidPage):
            object_list = paginator.page(paginator.num_pages).object_list
            page = num_pages
        if paginator.num_pages > 10:
            low_range = []
            mid_range = []
            high_range = []
            low_range = range(1, 6)
            high_range = range(paginator.num_pages - 4, paginator.num_pages + 1)
            if page < 10:
                low_range += range(6, min(paginator.num_pages,page + 5))
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
                ranges.append(range((round(min(paginator.num_pages, page+3)/10) + 1)*10, paginator.num_pages - 10, 10))
                ranges.append(high_range)

        else:
            ranges.append(paginator.page_range)

    context_vars = {
        'partial_base':partial_base,
        'partial_header':partial_header,
        'partial_row':partial_row,
        'paginator_template':paginator_template,
        'results_title':results_title,
        template_object_name:object_list, # for custom templates
        'object_list':object_list, # allow generic templates to still
                                          # access the object list in the same way
        'paginator':paginator,
        'filter_forms':filter_form_instances,
        'action_forms':action_form_instances,
        'paginated':paginated,
        'total':total,
        'selectable':selectable,
        'columns':columns,
        'sort_column':sort_column,
        'sort_ascending':sort_ascending,
        'page':page,
        'ranges':ranges,
        'selected':selected,
        'status_message':status_message,
        'status_message_type':status_message_type,
        'base_template':'layout.html',
    }
    context_vars.update(kwargs)
    return render_to_response(response_template,context_vars,context_instance=RequestContext(request))

#from .forms import ModuleForm
#class FormModules(ModuleForm):
#    modules
#    def setModuleParams(self, dashboard, module=None):
#        pass
def generic_dashboard(request,
                      slug,
                      module_types=[],
                      base_template='generic/dashboard_base.html',
                      module_partial_template='generic/partials/module.html',
                      num_columns=2):

    module_dict = {}
    # Create mapping of module names to module forms
    for view_name, module_form, module_title in module_types:
        module_dict[view_name] = module_form

    module_instances = [(view_name, module_form(), module_title) for view_name, module_form, module_title in module_types]
    if request.method=='POST':
        # FIXME pass action variable, set defaults, do sane things
        if request.POST.get('action',None) == 'createmodule':
            form = module_dict[request.POST['module_type']](request.POST)
            if form.is_valid():
                dashboard = Dashboard.objects.get(user=request.user.pk, slug=slug)
                module = form.setModuleParams(dashboard)
                return render_to_response(module_partial_template,
                                          {
                                           'mod':module,
                                          },context_instance=RequestContext(request))
        else:
            data=request.POST.lists()
            for col_val, offset_list in data:
                offset = 0
                column = int(col_val)
                old_user_modules=Dashboard.objects.get(user=request.user.pk, slug=slug).modules.values_list('pk', flat=True).distinct()
                new_user_modules=[]
                for mod_pk in offset_list:
                    mod_pk = int(mod_pk)
                    new_user_modules.append(mod_pk)
                    module = Module.objects.get(pk=mod_pk)
                    module.offset = offset
                    module.column = column
                    module.save()
                    offset += 1
                for mod in old_user_modules:
                    if not mod in new_user_modules:
                        Dashboard.objects.get(user=request.user.pk, slug=slug).modules.get(pk=mod).delete()
            return HttpResponse(status=200)

        print data

    dashboard = Dashboard.objects.get(user=request.user.pk, slug=slug)
    modules = [{'col':i, 'modules':[]} for i in range(0, num_columns)]
    columns = dashboard.modules.values_list('column', flat=True).distinct()
    print columns
    for col in columns:
        modules[col]['modules'] = list(dashboard.modules.filter(column=col).order_by('offset'))

    return render_to_response(base_template,
                              {
                               'modules':modules,
                               'module_types':module_instances,
                               'module_partial_template':module_partial_template,
                               'location':'lid', 
                              },context_instance=RequestContext(request))

def dummy(request):
    return HttpResponse('dummy content here')

def dummy2(request):
    return HttpResponse('dummy2 content here')

def dummy3(request):
    return HttpResponse('dummy3 content here')
