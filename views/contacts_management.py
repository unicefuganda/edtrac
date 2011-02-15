from django.template import RequestContext
from django.shortcuts import  render_to_response
from rapidsms.models import Contact
from contact.views.forms import  NewContactForm,freeSearchForm,contactsForm
from django.core.paginator import Paginator, InvalidPage
from status160.models import  Team
from django.http import Http404,HttpResponseRedirect

def index(request,template,partial, form_types=[], action_types=[]):
    action_form_instances=[]
    filter_form_instances=[]
    contacts_form=contactsForm()
    qs=Contact._default_manager.all()

    for f_form in form_types:

        temp_form = f_form()
        filter_form_instances.append(temp_form)

    for a_form in action_types:
        temp_form = a_form()
        action_form_instances.append(temp_form)

    return render_to_response(template, {'action_forms':action_form_instances,'contacts_form':contacts_form,'filter_form_instances':filter_form_instances, 'partial':partial}, context_instance=RequestContext(request))

def contacts_list(request, page=None,form_types=[]):
    """ view that works with the contacts form to handle the pagination"""

    if request.session.get('filtered',None):
        contact_list=request.session['contact_list']
    else:
        contact_list = Contact.objects.all()

    if request.method=='POST':
        for form in form_types:
            filter_form=form(request.POST)
            if filter_form.is_valid():
                if form_types.index(form)==0:
                    contact_list = filter_form.filter()
                else:
                    contact_list=contact_list | filter_form.filter()
        request.session['contact_list']=contact_list
        request.session['filtered']=True
        paginator = Paginator(contact_list, 20, allow_empty_first_page=True)
        contacts = paginator.page(1)
        return render_to_response('contact/partials/contacts_list.html', {'contacts':contacts})



    paginator = Paginator(contact_list, 20, allow_empty_first_page=True)
    if not page:
        page = request.GET.get('page', 1)
    try:
        page_number = int(page)
    except ValueError:
        if page == 'last':
            page_number = paginator.num_pages
        else:
        # Page is not 'last', nor can it be converted to an int.
            raise Http404
    try:
        contacts = paginator.page(page_number)
    except InvalidPage:
        raise Http404
    return render_to_response('contact/partials/contacts_list.html', {'contacts':contacts, "paginator":paginator},
                              context_instance=RequestContext(request))

def add_contact(request):
    if request.method=="POST":
        contact_form=NewContactForm(request.POST)
        if contact_form.is_valid():
            contact_form.save()

    return HttpResponseRedirect("/contact/index")

def form_actions(request,actions_list=[]):
    if request.method=="POST":
        contact_form_instance=contactsForm(request.POST)
        if "all" in request.POST:
            contacts=Contact.objects.all()
        else:
            if contact_form_instance.is_valid():
                contacts=contact_form_instance.cleaned_data['contacts']

        for form in actions_list:
            aform=form(request.POST,contacts)
            if a_form.is_valid():
                a_form.perform()
    return HttpResponseRedirect('/contact/index')

def new_contact(request):
    new_contact_form = NewContactForm()
    return render_to_response('contact/partials/new_contact.html', {'new_contact_form':new_contact_form})



