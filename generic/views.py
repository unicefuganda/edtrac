from django.template import RequestContext
from django.shortcuts import  render_to_response
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import Http404,HttpResponseServerError,HttpResponseRedirect
from django import forms

class SearchForm(forms.Form):
    """ concrete implementation of filter form """
    term = forms.CharField(max_length=100)
    action_label = 'awesome'

    def filter(self, queryset):
        return queryset.filter(text__icontains=self.data['term'])

    def perform(self, results):
        for r in results:
            print r
        return "Worked!"

def generic(request,
            model=None,
            template_object_name='object_list',
            base_template='generic/base.html',
            partial_base='generic/partials/partial_base.html',
            partial_header='generic/partials/partial_header.html',
            partial_row='generic/partials/partial_row.html',
            paginator_template='generic/partials/pagination.html',
            paginated=True,
            objects_per_page=25,
            filter_forms=[],
            action_forms=[]):
    if not model:
        return HttpResponseServerError

    object_list=model.objects.all()
    filter_form_instances = []
    action_form_instances = []
    page = 1
    selected=False
    status_message=''

    if request.method == 'POST':
        page_action = request.POST.get('page_action', '')
        action_taken = request.POST.get('action', '')
        if page_action:
            object_list = request.session['object_list']
            try:
                page = int(request.POST.get('page_num', '1'))
            except ValueError:
                pass
        elif action_taken:
            class ResultsForm(forms.Form):
                results = forms.ModelMultipleChoiceField(queryset=model.objects.all(), widget=forms.CheckboxSelectMultiple())
            resultsform = ResultsForm(request.POST)
            if resultsform.is_valid():
                results = resultsform.cleaned_data['results']
                class_dict = {}
                for action_class in action_forms:
                    form_instance = action_class()
                    fully_qualified_class_name = "%s.%s" % (form_instance.__module__, form_instance.__class__.__name__)
                    class_dict[fully_qualified_class_name] = action_class

                action_class = class_dict[action_taken]
                action_instance = action_class()
                status_message = action_instance.perform(results)

        else:
            for form_class in filter_forms:
                form_instance = form_class(request.POST)
                object_list = form_instance.filter(object_list)
        selected = True
        response_template = partial_base
    else:
        for filter_class in filter_forms:
            form_instance = filter_class()
            filter_form_instances.append(form_instance)
        for action_class in action_forms:
            form_instance = action_class()
            fully_qualified_class_name = "%s.%s" % (form_instance.__module__, form_instance.__class__.__name__)
            action_form_instances.append((fully_qualified_class_name, form_instance,))
        response_template = base_template

    request.session['object_list'] = object_list

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

    return render_to_response(response_template, {
            'partial_base':partial_base,
            'partial_header':partial_header,
            'partial_row':partial_row,
            'paginator_template':paginator_template,
            template_object_name:object_list, # for custom templates
            'object_list':object_list,        # allow generic templates to still
                                              # access the object list in the same way
            'paginator':paginator,
            'filter_forms':filter_form_instances,
            'action_forms':action_form_instances,
            'paginated':paginated,
            'page':page,
            'ranges':ranges,
            'selected':selected,
            'status_message':status_message,
        },context_instance=RequestContext(request))