from django.template import RequestContext
from django.shortcuts import  render_to_response
from rapidsms.models import Contact
from contact.forms import NewContactForm,FreeSearchForm
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404,HttpResponseRedirect
from . import forms

def add_contact(request):

    if request.method=="POST":
        contact_form=NewContactForm(request.POST)
        if contact_form.is_valid():
            contact_form.save()

    return HttpResponseRedirect("/contact/index/")

def new_contact(request):

    new_contact_form = NewContactForm()
    return render_to_response('contact/partials/new_contact.html', {'new_contact_form':new_contact_form})


