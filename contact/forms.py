#!/usr/bin/python
# -*- coding: utf-8 -*-
from django import forms
from rapidsms.models import Contact,Connection
from django.forms.widgets import Widget
from django.template.loader import get_template
from django.template.context import Context
from django.core.paginator import Paginator, Page
from django.contrib.auth.models import Group
from django.db.models import Q
from rapidsms_httprouter.router import get_router, \
    start_sending_mass_messages, stop_sending_mass_messages
from rapidsms.messages.outgoing import OutgoingMessage
from generic.forms import ActionForm, FilterForm
from ureport.models import MassText
from django.contrib.sites.models import Site
from threading import Thread, Lock
from simple_locations.models import Area
import time
from django.conf import settings

send_masstext_lock = Lock()

class FilterGroupsForm(FilterForm):

    """ concrete implementation of filter form """
    # This may seem like a hack, but this allows time for the Contact model's
    # default manage to be replaced at run-time.  There are many applications
    # for that, such as filtering contacts by site_id (as is done in the
    # authsites app, see github.com/daveycrockett/authsites).
    # This does, however, also make the polling app independent of authsites.
    def __init__(self, data=None, **kwargs):
        self.request=kwargs.pop('request')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)
        if hasattr(Contact, 'groups'):
            if self.request.user.is_authenticated():
                if self.request.user.groups.order_by('-pk') == Group.objects.order_by('-pk'):
                    choices = ((-1,'No Group'),) + tuple([(int(g.pk), g.name) for g in Group.objects.all().order_by('name')])
                    self.fields['groups'] = forms.MultipleChoiceField(choices=choices, required=True)
                else:
                    self.fields['groups'] = forms.ModelMultipleChoiceField(queryset=Group.objects.filter(pk__in=self.request.user.groups.values_list('pk',flat=True)), required=False)
            else:
                choices = ((-1,'No Group'),) + tuple([(int(g.pk), g.name) for g in Group.objects.all().order_by('name')])
                self.fields['groups'] = forms.MultipleChoiceField(choices=choices, required=True)


    def filter(self, request, queryset):
        groups_pk = self.cleaned_data['groups']
        if '-1' in groups_pk:
            groups_pk.remove('-1')
            if len(groups_pk):
                return queryset.filter(Q(groups=None) | Q(groups__in=groups_pk))
            else:
                return queryset.filter(groups=None)
        else:
            return queryset.filter(groups__in=groups_pk)

class NewContactForm(forms.ModelForm):

    class Meta:
        model = Contact


class FreeSearchForm(FilterForm):

    """ concrete implementation of filter form 
        TO DO: add ability to search for multiple search terms separated by 'or'
    """

    search = forms.CharField(max_length=100, required=True, label="Free-form search", help_text="Use 'or' to search for multiple names")

    def filter(self, request, queryset):
        search = self.cleaned_data['search']
        return queryset.filter(Q(name__icontains=search)
                               | Q(reporting_location__name__icontains=search)
                               | Q(connection__identity__icontains=search))

class FreeSearchTextForm(FilterForm):

    """ concrete implementation of filter form """

    search = forms.CharField(max_length=100, required=True, label="Free-form search", help_text="Use 'or' to search for multiple names")

    def filter(self, request, queryset):
        search = self.cleaned_data['search']
        return queryset.filter(text__icontains=search)

class HandledByForm(FilterForm):
    type = forms.ChoiceField(choices=(('','-----'), ('poll', 'Poll Response'), ('rapidsms_xforms', 'Report'), ('*', 'Other'),))

    def filter(self, request, queryset):
        handled_by = self.cleaned_data['type']
        if handled_by == '':
            return queryset
        elif handled_by == '*':
            return queryset.filter(application=None)
        else:
            return queryset.filter(application=handled_by)


class DistictFilterForm(FilterForm):

    """ filter cvs districs on their districts """

    district = forms.ChoiceField(choices=(('', '-----'), (-1,
                                 'No District')) + tuple([(int(d.pk),
                                 d.name) for d in
                                 Area.objects.filter(kind__slug='district'
                                 ).order_by('name')]))

    def filter(self, request, queryset):
        district_pk = self.cleaned_data['district']
        if district_pk == '':
            return queryset
        elif int(district_pk) == -1:
            return queryset.filter(reporting_location=None)
        else:

            try:
                district = Area.objects.get(pk=district_pk)
            except Area.DoesNotExist:
                district = None
            if district:
                return queryset.filter(reporting_location__in=district.get_descendants(include_self=True))
            else:
                return queryset

class DistictFilterMessageForm(FilterForm):

    """ filter cvs districs on their districts """

    district = forms.ChoiceField(choices=(('', '-----'), (-1,
                                 'No District')) + tuple([(int(d.pk),
                                 d.name) for d in
                                 Area.objects.filter(kind__slug='district'
                                 ).order_by('name')]))

    def filter(self, request, queryset):
        district_pk = self.cleaned_data['district']
        if district_pk == '':
            return queryset
        elif int(district_pk) == -1:
            return queryset.filter(Q(connection__contact=None) | Q(connection__contact__reporting_location=None))
        else:
            try:
                district = Area.objects.get(pk=district_pk)
            except Area.DoesNotExist:
                district = None
            if district:
                return queryset.filter(connection__contact__reporting_location__in=district.get_descendants(include_self=True))
            else:
                return queryset


class MassTextForm(ActionForm):

    text = forms.CharField(max_length=160, required=True)
    action_label = 'Send Message'

    class MassTexter(Thread):
        def __init__(self, connections, text, user, **kwargs):
            Thread.__init__(self, **kwargs)
            self.connections = connections
            self.text = text
            self.user = user

        def run(self):
            time.sleep(5)
            global send_masstext_lock
            send_masstext_lock.acquire()
            router = get_router()
            start_sending_mass_messages()
            mass_text = MassText.objects.create(user=self.user,
                    text=self.text)
            mass_text.sites.add(Site.objects.get_current())
            for conn in Connection.objects.filter(pk__in=self.connections):
                mass_text.contacts.add(conn.contact)
                outgoing = OutgoingMessage(conn, self.text)
                print "sending to %s" % str(conn.identity)
                router.handle_outgoing(outgoing)
            stop_sending_mass_messages()
            send_masstext_lock.release()

    def perform(self, request, results):
        if results is None or len(results) == 0:
            return ('A message must have one or more recipients!', 'error')

        if request.user and request.user.has_perm('ureport.can_message'):
            connections = \
                list(Connection.objects.filter(contact__in=results).values_list('pk',flat=True).distinct())

            text = self.cleaned_data['text']
            text = text.replace('%', '%%')

            worker = self.MassTexter(connections, text, request.user)
            if len(connections) > 100:
                worker.start()
            else:
                worker.run()

            return ('Message successfully sent to %d numbers' % len(connections), 'success',)
        else:
            return ("You don't have permission to send messages!", 'error',)

class ReplyTextForm(ActionForm):

    text = forms.CharField(max_length=160, required=True)
    action_label = 'Reply to selected'

    def perform(self, request, results):
        if results is None or len(results) == 0:
            return ('A message must have one or more recipients!', 'error')

        if request.user and request.user.has_perm('ureport.can_message'):
            router = get_router()
            text = self.cleaned_data['text']
            start_sending_mass_messages()
            for msg in results:
                outgoing = OutgoingMessage(msg.connection, text)
                router.handle_outgoing(outgoing, msg)
            stop_sending_mass_messages()
            return ('%d messages sent successfully' % results.count(), 'success',)
        else:
            return ("You don't have permission to send messages!", 'error',)

class AssignGroupForm(ActionForm):

    action_label = 'Assign to group(s)'

    # This may seem like a hack, but this allows time for the Contact model's
    # default manage to be replaced at run-time.  There are many applications
    # for that, such as filtering contacts by site_id (as is done in the
    # authsites app, see github.com/daveycrockett/authsites).
    # This does, however, also make the polling app independent of authsites.
    def __init__(self, data=None, **kwargs):
        self.request=kwargs.pop('request')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)
        if hasattr(Contact, 'groups'):
            if self.request.user.is_authenticated():
                self.fields['groups'] = forms.ModelMultipleChoiceField(queryset=Group.objects.filter(pk__in=self.request.user.groups.values_list('pk',flat=True)), required=False)
            else:
                self.fields['groups'] = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)

    def perform(self, request, results):
        groups = self.cleaned_data['groups']
        for c in results:
            for g in groups:
                c.groups.add(g)
        return ('%d Contacts assigned to %d groups.' % (len(results), len(groups)), 'success',)