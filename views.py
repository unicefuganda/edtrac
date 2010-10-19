from django.db import transaction
from django.views.decorators.http import require_GET, require_POST
from django.template import RequestContext
from django.shortcuts import redirect, get_object_or_404, render_to_response
from django.conf import settings
from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Poll, Category, Rule, Response, ResponseCategory, STARTSWITH_PATTERN_TEMPLATE, CONTAINS_PATTERN_TEMPLATE
from rapidsms.models import Contact
from simple_locations.models import Area
from mptt.forms import TreeNodeChoiceField

from xml.dom.minidom import parse, parseString

# CSV Export
@require_GET
def responses_as_csv(req, pk):
    poll = get_object_or_404(Poll, pk=pk)

    responses = poll.responses.all().order_by('-pk')

    resp = render_to_response(
        "polls/responses.csv", 
        {'responses': responses},
        mimetype="text/csv",
        context_instance=RequestContext(req))
    resp['Content-Disposition'] = 'attachment;filename="%s.csv"' % poll.name
    return resp

@require_GET
def polls(req): 
    polls = Poll.objects.all()
    breadcrumbs = (('Polls', ''),)
    return render_to_response(
        "polls/poll_index.html", 
        { 'polls': polls, 'breadcrumbs': breadcrumbs },
        context_instance=RequestContext(req))

class NewPollForm(forms.Form): # pragma: no cover
    
    TYPE_YES_NO = 'yn'
    
    type = forms.ChoiceField(
               required=True,
               choices=(
                    (Poll.TYPE_TEXT, 'Free-form'),
                    (TYPE_YES_NO, 'Yes/No Question'),                    
                    (Poll.TYPE_NUMERIC, 'Numeric Response'),
                    (Poll.TYPE_LOCATION, 'Location-based'),
                    (Poll.TYPE_REGISTRATION, 'Name/registration-based'),
                ))
    contacts = forms.ModelMultipleChoiceField(queryset=Contact.objects.all())
    name = forms.CharField(max_length=32, required=True)
    question = forms.CharField(max_length=160, required=True)
    default_response = forms.CharField(max_length=160, required=True)
    start_immediately = forms.BooleanField(required=False)

class EditPollForm(forms.ModelForm): # pragma: no cover
    class Meta:
        model = Poll
        fields = ('name', 'contacts', 'default_response')

def new_poll(req):
    if req.method == 'POST':
        form = NewPollForm(req.POST)
        if form.is_valid():
            # create our XForm
            question = form.cleaned_data['question']
            default_response = form.cleaned_data['default_response']
            contacts = form.cleaned_data['contacts']
            name = form.cleaned_data['name']
            if form.cleaned_data['type'] == Poll.TYPE_TEXT:
                poll = Poll.create_freeform(name, question, default_response, contacts, req.user)
            elif form.cleaned_data['type'] == Poll.TYPE_REGISTRATION:
                poll = Poll.create_registration(name, question, default_response, contacts, req.user)                
            elif form.cleaned_data['type'] == Poll.TYPE_NUMERIC:
                poll = Poll.create_numeric(name, question, default_response, contacts, req.user)
            elif form.cleaned_data['type'] == NewPollForm.TYPE_YES_NO:
                poll = Poll.create_yesno(name, question, default_response, contacts, req.user)
            elif form.cleaned_data['type'] == Poll.TYPE_LOCATION:
                poll = Poll.create_location_based(name, question, default_response, contacts, req.user)
            if form.cleaned_data['start_immediately']:
                poll.start()
            
            return redirect("/polls/%d/view/" % poll.pk)
    else:
        form = NewPollForm()

    return render_to_response(
        "polls/poll_create.html", { 'form': form },
        context_instance=RequestContext(req))

def view_poll(req, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    categories = Category.objects.filter(poll=poll)
    breadcrumbs = (('Polls', '/polls'),('Edit Poll', ''))
    return render_to_response("polls/poll_view.html", 
        { 'poll': poll, 'categories': categories, 'category_count' : len(categories), 'breadcrumbs' : breadcrumbs },
        context_instance=RequestContext(req))

def view_report(req, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    breadcrumbs = (('Polls', '/polls'),)
    template = None
    context = { 'poll':poll, 'breadcrumbs':breadcrumbs }
    if poll.type == Poll.TYPE_TEXT:
        template = "polls/poll_report_text.html"
        context.update(poll.get_text_report_data())
        pass
    elif poll.type == Poll.TYPE_NUMERIC:
        template = "polls/poll_report_numeric.html"
        context.update(poll.get_numeric_report_data())
        pass
    else:
        return render_to_response(
        "polls/poll_index.html",
        { 'polls': Poll.objects.all(), 'breadcrumbs': (('Polls', ''),) },
        context_instance=RequestContext(req))
    return render_to_response(template, context, context_instance=RequestContext(req))

def view_poll_details(req, form_id):
    poll = get_object_or_404(Poll, pk=form_id)
    return render_to_response("polls/poll_details.html",
        { 'poll': poll },
        context_instance=RequestContext(req))

def edit_poll(req, poll_id):
    poll = get_object_or_404(Poll,pk=poll_id)
    categories = Category.objects.filter(poll=poll)

    breadcrumbs = (('Polls', '/polls'),('Edit Poll', ''))

    if req.method == 'POST':
        form = EditPollForm(req.POST, instance=poll)
        if form.is_valid():
            poll = form.save()
            return render_to_response("polls/poll_details.html", 
                {"poll" : poll},
                context_instance=RequestContext(req))
    else:
        form = EditPollForm(instance=poll)

    return render_to_response("polls/poll_edit.html", 
        { 'form': form, 'poll': poll, 'categories': categories, 'category_count' : len(categories), 'breadcrumbs' : breadcrumbs },
        context_instance=RequestContext(req))

class CategoryForm(forms.ModelForm):
    name = forms.CharField(max_length=50, required=True)
    default = forms.BooleanField(required=False)
    response = forms.CharField(max_length=160, required=False)
    priority = forms.IntegerField(required=False, widget=forms.Select(
            choices=tuple([('', '---')] + [(i,"%d" % i) for i in range(1,11)])))
    color = forms.CharField(required=False, max_length=6, widget=forms.Select(choices=(
                (None, '---'),
                ('ff9977', 'red'),
                ('99ff77', 'green'),
                ('7799ff', 'blue'),
                ('ffff77', 'yellow'))))
    class Meta:
        model = Category
        fields = ('name', 'priority', 'color', 'default', 'response')


def view_responses(req, poll_id):
    poll = get_object_or_404(Poll,pk=poll_id)

    responses = poll.responses.all().order_by('-pk')

    breadcrumbs = (('Polls', '/polls'),('Responses', ''))
    
    return render_to_response("polls/responses.html", 
        { 'poll': poll, 'responses': responses, 'breadcrumbs': breadcrumbs, 'columns': columns_dict[poll.type]},
        context_instance=RequestContext(req))

class ResponseForm(forms.Form):
    def __init__(self, data=None, **kwargs):
        response = kwargs.pop('response')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)
        self.fields['categories'] = forms.ModelMultipleChoiceField(required=False, queryset=response.poll.categories.all(), initial=Category.objects.filter(pk=response.categories.values_list('category',flat=True)))

class NumericResponseForm(ResponseForm):
    value = forms.FloatField()

class LocationResponseForm(ResponseForm):
    value = TreeNodeChoiceField(queryset=Area.tree.all(),
                 level_indicator=u'+--', required=True)
    
class NameResponseForm(ResponseForm):
    value = forms.CharField()    

def _get_response_edit_form(response, data=None):
    if (response.poll.type == Poll.TYPE_TEXT):
        if data:
            return ResponseForm(data, response=response)
        else:
            return ResponseForm(response=response)
    if (response.poll.type == Poll.TYPE_NUMERIC):
        if data:
            return NumericResponseForm(data, response=response)
        else:
            return NumericResponseForm(response=response, initial={'value':response.eav.poll_number_value})
    if (response.poll.type == Poll.TYPE_LOCATION):
        if data:
            return LocationResponseForm(data, response=response)
        else:
            return LocationResponseForm(response=response, initial={'value':response.eav.poll_location_value})
    if (response.poll.type == Poll.TYPE_REGISTRATION):
        if data:
            return NameResponseForm(data, response=response)
        else:
            return NameResponseForm(response=response, initial={'value':response.eav.poll_text_value})


def apply_response(req, response_id):
    response = get_object_or_404(Response, pk=response_id)
    poll = response.poll
    if poll.type == Poll.TYPE_REGISTRATION:
        try:
            response.message.connection.contact.name = response.eav.poll_text_value
        except AttributeError:
            pass
    elif poll.type == Poll.TYPE_LOCATION:
        #FIXME: logic here?
        pass 
    
    responses = poll.responses.all().order_by('-pk')

    breadcrumbs = (('Polls', '/polls'),('Responses', ''))
    
    return render_to_response("polls/responses.html", 
        { 'poll': poll, 'responses': responses, 'breadcrumbs': breadcrumbs, 'columns': columns_dict[poll.type]},
        context_instance=RequestContext(req))
    

@transaction.commit_on_success
def edit_response(req, response_id):
    response = get_object_or_404(Response, pk=response_id)
    poll = response.poll 
    
    if req.method == 'POST':
        form = _get_response_edit_form(response, data=req.POST)
        if form.is_valid():       
            response.update_categories(form.cleaned_data['categories'], req.user)
            if poll.type == Poll.TYPE_NUMERIC:
                response.eav.poll_number_value = form.cleaned_data['value']
            elif poll.type == Poll.TYPE_LOCATION:
                response.eav.poll_location_value = form.cleaned_data['value']
            elif poll.type == Poll.TYPE_REGISTRATION:
                response.eav.poll_text_value = form.cleaned_data['value']
            response.save()
            return render_to_response(view_templates_dict[response.poll.type], 
                { 'response' : response },
                context_instance=RequestContext(req))
        else:
            return render_to_response(edit_templates_dict[response.poll.type], 
                            { 'response' : response, 'form':form },
                            context_instance=RequestContext(req))
    else:
        form = _get_response_edit_form(response)

    return render_to_response(edit_templates_dict[response.poll.type], 
        { 'form' : form, 'response': response },
        context_instance=RequestContext(req))

def view_response(req, response_id):
    response = get_object_or_404(Response, pk=response_id)
    return render_to_response(view_templates_dict[response.poll.type], 
        { 'response': response },
        context_instance=RequestContext(req))
    
def delete_response (req, response_id):
    response = get_object_or_404(Response, pk=response_id)
    poll = response.poll
    if req.method == 'POST':
        response.delete()
        
    return redirect("/polls/%d/responses/" % poll.pk)

def view_category(req, poll_id, category_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    category = get_object_or_404(Category, pk=category_id)
    return render_to_response("polls/category_view.html", 
        { 'poll': poll, 'category' : category },
        context_instance=RequestContext(req))
    
@transaction.commit_on_success
def edit_category (req, poll_id, category_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    category = get_object_or_404(Category, pk=category_id)
    if req.method == 'POST':
        form = CategoryForm(req.POST, instance=category)
        print form.errors
        if form.is_valid():
            if form.cleaned_data['default'] == True:
                Category.clear_defaults(poll)       
            category = form.save(commit=False)
            category.poll = poll
            category.save()
            return render_to_response("polls/category_view.html", 
                { 'form' : form, 'poll': poll, 'category' : category },
                context_instance=RequestContext(req))
        else:
            return render_to_response("polls/category_edit.html", 
                            { 'form' : form, 'poll': poll, 'category' : category },
                            context_instance=RequestContext(req))
    else:
        form = CategoryForm(instance=category)

    return render_to_response("polls/category_edit.html", 
        { 'form' : form, 'poll': poll, 'category' : category },
        context_instance=RequestContext(req))

def add_category(req, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    form = CategoryForm()

    if req.method == 'POST':
        form = CategoryForm(req.POST)
        if form.is_valid():
            if form.cleaned_data['default'] == True:
                for c in Category.objects.filter(poll=poll, default=True):
                    c.default=False
                    c.save()
            category = form.save(commit=False)
            category.poll = poll
            category.save()
            poll.categories.add(category)
            return render_to_response("polls/category_view.html", 
                { 'category' : category, 'form' : form, 'poll' : poll },
                context_instance=RequestContext(req))
    else:
        form = CategoryForm()

    return render_to_response("polls/category_edit.html", 
        { 'form' : form, 'poll' : poll },
        context_instance=RequestContext(req))

def delete_poll (req, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    if req.method == 'POST':
        poll.delete()
        
    return redirect("/polls")

def start_poll (req, poll_id):
    poll = Poll.objects.get(pk=poll_id)
    if req.method == 'POST':
        poll.start()
        
    return render_to_response("polls/poll_details.html", 
        {"poll" : poll},
        context_instance=RequestContext(req))

def end_poll (req, poll_id):
    poll = Poll.objects.get(pk=poll_id)
    if req.method == 'POST':
        poll.end()
        
    return render_to_response("polls/poll_details.html", 
        {"poll" : poll},
        context_instance=RequestContext(req))

def delete_category (req, poll_id, category_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    category = get_object_or_404(Category, pk=category_id)

    if req.method == 'POST':
        category.delete()
        
    return redirect("/polls/%d/edit/" % poll.pk)

class RuleForm(forms.ModelForm):
    rule_string = forms.CharField(max_length=256, required=True)
    rule_type = forms.CharField(max_length=2, required=False, widget=forms.Select(choices=Rule.RULE_CHOICES))
    class Meta:
        model = Rule
        fields = ('rule_type', 'rule_string')

@transaction.commit_on_success
def edit_rule(req, poll_id, category_id, rule_id) :
    
    poll = get_object_or_404(Poll, pk=poll_id)
    category = get_object_or_404(Category, pk=category_id)
    rule = get_object_or_404(Rule, pk=rule_id)
    
    if req.method == 'POST':
        form = RuleForm(req.POST, instance=rule)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.update_regex()
            rule.save()
            poll.reprocess_responses()
            return render_to_response("polls/table_row_view.html", 
                {  'columns' : rule_columns, 'buttons' : rule_buttons, 'item' : rule, 'form' : form, 'poll' : poll, 'category' : category },
                context_instance=RequestContext(req))
        else:
            return render_to_response("polls/table_row_edit.html", 
                { 'buttons' : save_button, 'item' : rule, 'form' : form, 'poll' : poll, 'category' : category },
                context_instance=RequestContext(req))
    else:
        form = RuleForm(instance=rule)
    
    return render_to_response("polls/table_row_edit.html", 
        { 'buttons' : save_button, 'form' : form, 'poll': poll, 'category' : category, 'item' : rule },
        context_instance=RequestContext(req))

@transaction.commit_on_success
def add_rule(req, poll_id, category_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    if poll.type != Poll.TYPE_TEXT:
        return HttpResponse(status=404)
    category = get_object_or_404(Category, pk=category_id)
    form = RuleForm()

    if req.method == 'POST':
        form = RuleForm(req.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.category = category
            rule.update_regex()
            rule.save()
            poll.reprocess_responses()
            return render_to_response("polls/table_row_view.html", 
                {  'columns' : rule_columns, 'buttons' : rule_buttons, 'item' : rule, 'form' : form, 'poll' : poll, 'category' : category },
                context_instance=RequestContext(req))
    else:
        form = RuleForm()

    return render_to_response("polls/table_row_edit.html", 
        { 'buttons' : save_button, 'form' : form, 'poll': poll, 'category' : category },
        context_instance=RequestContext(req))
    
def view_rule(req, poll_id, category_id, rule_id) :
    
    poll = get_object_or_404(Poll, pk=poll_id)
    category = get_object_or_404(Category, pk=category_id)
    rule = get_object_or_404(Rule, pk=rule_id)
    return render_to_response("polls/table_row_view.html", 
        { 'columns' : rule_columns, 'buttons' : rule_buttons, 'item' : rule, 'poll' : poll, 'category' : category },
        context_instance=RequestContext(req))
    
    
def view_rules(req, poll_id, category_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    category = get_object_or_404(Category, pk=category_id)
    rules = Rule.objects.filter(category=category)

    breadcrumbs = (('Polls', '/polls'),(poll.name, "/polls/%s/view/" % poll.pk), ("Categories", ''))

    return render_to_response("polls/rules.html", 
        {  'poll' : poll, 'category' : category, 'table' : rules, 'buttons' : rule_buttons, 'columns' : rule_columns, 'breadcrumbs': breadcrumbs },
        context_instance=RequestContext(req))

@transaction.commit_on_success
def delete_rule (req, poll_id, category_id, rule_id):
    rule = get_object_or_404(Rule, pk=rule_id)
    category = rule.category
    if req.method == 'POST':
        rule.delete()
    category.poll.reprocess_responses()
    return redirect("/polls/%s/category/%s/rules/" % (poll_id, category_id))

add_button = ({ "image" : "rapidsms/icons/silk/decline.png", 'click' : 'cancelAdd'}, 
              { "text" : "Add", "image" : "rapidsms/icons/silk/add.png" , 'click' : 'add'},)

save_button = ( { "image" : "rapidsms/icons/silk/decline.png", 'click' : 'cancelSave'},
                { "text" : "Save", "image" : "poll/icons/silk/bullet_disk.png", 'click' : 'saveRow'},)
rule_buttons = ({"image" : "rapidsms/icons/silk/delete.png", 'click' : 'deleteRow'},
                      { "text" : "Edit", "image" : "poll/icons/silk/pencil.png", 'click' : 'editRow'},)

rule_columns = (('Rule', 'rule_type_friendly'), ('Text', 'rule_string'))

columns_dict = {
    Poll.TYPE_LOCATION:(('Text','text'),('Location','location'),('Categories','categories')),
    Poll.TYPE_TEXT:(('Text', 'text'),('Categories','categories')),
    Poll.TYPE_NUMERIC:(('Text','text'),('Value','value'), ('Categories', 'categories')),
    Poll.TYPE_REGISTRATION:(('Text','text'),('Categories','categories')),
}

view_templates_dict = {
    Poll.TYPE_LOCATION:'polls/response_location_view.html',
    Poll.TYPE_TEXT:'polls/response_text_view.html',
    Poll.TYPE_NUMERIC:'polls/response_numeric_view.html',
    Poll.TYPE_REGISTRATION:'polls/response_registration_view.html',
}

edit_templates_dict = {
    Poll.TYPE_LOCATION:'polls/response_location_edit.html',
    Poll.TYPE_TEXT:'polls/response_text_edit.html',
    Poll.TYPE_NUMERIC:'polls/response_numeric_edit.html',
    Poll.TYPE_REGISTRATION:'polls/response_registration_edit.html',
}

