from django.template import RequestContext
from django.shortcuts import  render_to_response
from rapidsms.models import Contact
from contact.views.forms import contactsForm,NewContactForm
from django.core.paginator import Paginator, InvalidPage


filters={
    'poll':poll_filters
}



def poll_filters(request):
    if request.GET.get('value',None):
        contacts=Poll.objects.get(pk=poll).contacts.all()


    return users


def index(request):
    form=contactsForm()
    return render_to_response("contact/index.html",{'contact_form':form},context_instance=RequestContext(request))

def contacts_list(request,page=None):
    filter=request.GET.get('f',None)
    contact_list=Contact._default_manager.all()
    if filter:
        value=request.GET.get('value',None)
        contact_list=contact_list &
    else:
        contact_list=Contact._default_manager.all()
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
    return render_to_response('contact/partials/contacts_list.html',{'contacts':contacts,"paginator":paginator},context_instance=RequestContext(request))
        
def add_contact(request):
    contact=Contact.create(name=request.POST.get('name',''))

def render_filters(request):
    rensered=[]
    for filter in filters:
        rendered.append('<span>By '+filter['name'] )

    


def new_contact(request):
    new_contact_form=NewContactForm()
    return render_to_response('contact/partials/new_contact.html',{'new_contact_form':new_contact_form})


def search_filters(request):
    pass

