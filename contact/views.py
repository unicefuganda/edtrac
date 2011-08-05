from django.template import RequestContext
from django.shortcuts import  render_to_response, get_object_or_404, redirect
from rapidsms.models import Contact, Connection
from contact.forms import NewContactForm, FreeSearchForm
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404, HttpResponseRedirect
from rapidsms_httprouter.models import STATUS_CHOICES, DIRECTION_CHOICES, Message
from rapidsms.messages.outgoing import OutgoingMessage
from django.contrib.auth.decorators import login_required
from . import forms
from .forms import ReplyForm
from rapidsms_httprouter.router import get_router

def add_contact(request):

    if request.method == "POST":
        contact_form = NewContactForm(request.POST)
        if contact_form.is_valid():
            contact_form.save()

    return HttpResponseRedirect("/contact/index/")

def new_contact(request):

    new_contact_form = NewContactForm()
    return render_to_response('contact/partials/new_contact.html', {'new_contact_form':new_contact_form})

@login_required
def view_message_history(request, connection_id):
    """
        This view lists all (sms message) correspondence between 
        RapidSMS and a User 
        
    """
    direction_choices = DIRECTION_CHOICES
    status_choices = STATUS_CHOICES
    reply_form = ReplyForm()
    connection = get_object_or_404(Connection, pk=connection_id)

    if connection.contact:
        messages = Message.objects.filter(connection__contact=connection.contact)
    else:
        messages = Message.objects.filter(connection=connection)
    messages = messages.order_by('-date')

    total_incoming = messages.filter(direction="I").count()
    total_outgoing = messages.filter(direction="O").count()
    latest_message = None
    if total_incoming:
        latest_message = messages.filter(direction="I").latest('date')

    if request.method == 'POST':
        reply_form = ReplyForm(request.POST)
        if reply_form.is_valid():
            if Connection.objects.filter(identity=reply_form.cleaned_data['recipient']).count():
                text = reply_form.cleaned_data['message']
                conn = Connection.objects.filter(identity=reply_form.cleaned_data['recipient'])[0]
                in_response_to = reply_form.cleaned_data['in_response_to']
                outgoing = OutgoingMessage(conn, text)
                get_router().handle_outgoing(outgoing, in_response_to)
                return redirect("/contact/%d/message_history/" % connection.pk)
            else:
                reply_form.errors.setdefault('short_description', ErrorList())
                reply_form.errors['recipient'].append("This number isn't in the system")

    return render_to_response("contact/message_history.html", {
        "messages": messages,
        "stats_latest_message": latest_message,
        "stats_total_incoming": total_incoming,
        "stats_total_outgoing": total_outgoing,
        "connection": connection,
        "direction_choices": direction_choices,
        "status_choices": status_choices,
        "replyForm": reply_form
    }, context_instance=RequestContext(request))
