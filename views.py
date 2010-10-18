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
                    (Poll.TYPE_NUMERIC, 'Numeric Response'),
                    (TYPE_YES_NO, 'Yes/No Question')
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
            elif form.cleaned_data['type'] == Poll.TYPE_NUMERIC:
                poll = Poll.create_numeric(name, question, default_response, contacts, req.user)
            elif form.cleaned_data['type'] == NewPollForm.TYPE_YES_NO:
                poll = Poll.create_yesno(name, question, default_response, contacts, req.user)
                
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
        { 'poll': poll, 'responses': responses, 'breadcrumbs': breadcrumbs },
        context_instance=RequestContext(req))

class ResponseForm(forms.Form):
    def __init__(self, data=None, **kwargs):
        response = kwargs.pop('response')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)
        self.fields['categories'] = forms.ModelMultipleChoiceField(required=False, queryset=response.poll.categories.all(), initial=Category.objects.filter(pk=response.categories.values_list('category',flat=True)))            
         
@transaction.commit_on_success
def edit_response(req, response_id):
    response = get_object_or_404(Response, pk=response_id)
    poll = response.poll 
    
    if req.method == 'POST':
        form = ResponseForm(req.POST, response=response)
        if form.is_valid():       
            response.update_categories(form.cleaned_data['categories'], req.user)
            return render_to_response("polls/response_view.html", 
                { 'response' : response },
                context_instance=RequestContext(req))
        else:
            return render_to_response("polls/response_edit.html", 
                            { 'response' : response, 'form':form },
                            context_instance=RequestContext(req))
    else:
        form = ResponseForm(response=response)

    return render_to_response("polls/response_edit.html", 
        { 'form' : form, 'response': response },
        context_instance=RequestContext(req))

def view_response(req, response_id):
    response = get_object_or_404(Response, pk=response_id)
    return render_to_response("polls/response_view.html", 
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
