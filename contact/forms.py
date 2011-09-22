#!/usr/bin/python
# -*- coding: utf-8 -*-
from django import forms
from rapidsms.models import Contact, Connection
from django.forms.widgets import Widget
from django.template.loader import get_template
from django.template.context import Context
from django.core.paginator import Paginator, Page
from django.contrib.auth.models import Group
from django.db.models import Q
from rapidsms_httprouter.router import get_router, \
    start_sending_mass_messages, stop_sending_mass_messages
from rapidsms_httprouter.models import Message
from rapidsms.messages.outgoing import OutgoingMessage
from generic.forms import ActionForm, FilterForm
from ureport.models import MassText
from django.contrib.sites.models import Site
from rapidsms.contrib.locations.models import Location
from uganda_common.forms import SMSInput
from django.conf import settings
import datetime
from rapidsms_httprouter.models import Message
from django.forms.util import ErrorList


class ReplyForm(forms.Form):
    recipient = forms.CharField(max_length=20)
    message = forms.CharField(max_length=160, widget=forms.TextInput(attrs={'size':'60'}))
    in_response_to = forms.ModelChoiceField(queryset=Message.objects.filter(direction='I'), widget=forms.HiddenInput())


class FilterGroupsForm(FilterForm):

    """ concrete implementation of filter form """
    # This may seem like a hack, but this allows time for the Contact model's
    # default manage to be replaced at run-time.  There are many applications
    # for that, such as filtering contacts by site_id (as is done in the
    # authsites app, see github.com/daveycrockett/authsites).
    # This does, however, also make the polling app independent of authsites.
    def __init__(self, data=None, **kwargs):
        self.request = kwargs.pop('request')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)
        if hasattr(Contact, 'groups'):
            if self.request.user.is_authenticated():
                if self.request.user.groups.order_by('-pk') == Group.objects.order_by('-pk'):
                    choices = ((-1, 'No Group'),) + tuple([(int(g.pk), g.name) for g in Group.objects.all().order_by('name')])
                    self.fields['groups'] = forms.MultipleChoiceField(choices=choices, required=True)
                else:
                    self.fields['groups'] = forms.ModelMultipleChoiceField(queryset=Group.objects.filter(pk__in=self.request.user.groups.values_list('pk', flat=True)), required=True)
            else:
                choices = ((-1, 'No Group'),) + tuple([(int(g.pk), g.name) for g in Group.objects.all().order_by('name')])
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

    search = forms.CharField(max_length=100, required=False, label="Free-form search",
                             help_text="Use 'or' to search for multiple names")

    def filter(self, request, queryset):
        search = self.cleaned_data['search']
        if search == "":
            return queryset
        else:
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
    type = forms.ChoiceField(
            choices=(('', '-----'), ('poll', 'Poll Response'), ('rapidsms_xforms', 'Report'), ('*', 'Other'),),\
            required=False)

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
                                 Location.objects.filter(type__slug='district'
                                 ).order_by('name')]),required=False)

    def filter(self, request, queryset):
        district_pk = self.cleaned_data['district']
        if district_pk == '':
            return queryset
        elif int(district_pk) == -1:
            return queryset.filter(reporting_location=None)
        else:

            try:
                district = Location.objects.get(pk=district_pk)
            except Location.DoesNotExist:
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
                                 Location.objects.filter(type__slug='district'
                                 ).order_by('name')]),required=False)

    def filter(self, request, queryset):
        district_pk = self.cleaned_data['district']
        if district_pk == '':
            return queryset
        elif int(district_pk) == -1:
            return queryset.filter(Q(connection__contact=None) | Q(connection__contact__reporting_location=None))
        else:
            try:
                district = Location.objects.get(pk=district_pk)
            except Location.DoesNotExist:
                district = None
            if district:
                return queryset.filter(connection__contact__reporting_location__in=district.get_descendants(include_self=True))
            else:
                return queryset

class MassTextForm(ActionForm):

    text = forms.CharField(max_length=160, required=True,widget=SMSInput())
    action_label = 'Send Message'

    def clean_text(self):
        cleaned_data=self.cleaned_data
        text = cleaned_data['text']

        #replace common MS-word characters with SMS-friendly characters
        for find, replace in [(u'\u201c', '"'),
                              (u'\u201d', '"'),
                              (u'\u201f', '"'),
                              (u'\u2018', "'"),
                              (u'\u2019', "'"),
                              (u'\u201B', "'"),
                              (u'\u2013', "-"),
                              (u'\u2014', "-"),
                              (u'\u2015', "-"),
                              (u'\xa7', "$"),
                              (u'\xa1', "i"),
                              (u'\xa4', ''),
                              (u'\xc4', 'A')]:
            text = text.replace(find, replace)
        cleaned_data['text']=text
        return cleaned_data

    def perform(self, request, results):
        if results is None or len(results) == 0:
            return ('A message must have one or more recipients!', 'error')

        if request.user and request.user.has_perm('ureport.can_message'):
            connections = \
                list(Connection.objects.filter(contact__in=results).distinct())

            text = self.cleaned_data['text']
            text = text.replace('%', u'\u0025')

            messages = Message.mass_text(text, connections)

            MassText.bulk.bulk_insert(send_pre_save=False,
                    user=request.user,
                    text=text,
                    contacts=list(results))
            masstexts = MassText.bulk.bulk_insert_commit(send_post_save=False, autoclobber=True)
            masstext = masstexts[0]
            if settings.SITE_ID:
                masstext.sites.add(Site.objects.get_current())

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
        self.request = kwargs.pop('request')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)
        if hasattr(Contact, 'groups'):
            if self.request.user.is_authenticated():
                self.fields['groups'] = forms.ModelMultipleChoiceField(queryset=Group.objects.filter(pk__in=self.request.user.groups.values_list('pk', flat=True)), required=False)
            else:
                self.fields['groups'] = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)

    def perform(self, request, results):
        groups = self.cleaned_data['groups']
        for c in results:
            for g in groups:
                c.groups.add(g)
        return ('%d Contacts assigned to %d groups.' % (len(results), len(groups)), 'success',)

class FlaggedForm(FilterForm):

    """ filter flagged/unflagged messages form """

    flagged = forms.ChoiceField(choices=(('', '-----'), (1, 'Flagged'), (0, 'Not flagged'),))

    def filter(self, request, queryset):
        flagged = self.cleaned_data['flagged']
        if flagged == '':
            return queryset
        elif int(flagged) == 1:
            return queryset.exclude(flags=None)
        else:
            return queryset.filter(flags=None)

class FlagMessageForm(ActionForm):

    """ flag/unflag messages action form """

    flag = forms.ChoiceField(choices=(('', '-----'), ('flag', 'Flag'), ('unflag', 'Unflag'),))
    action_label = 'Flag/Unflag selected'

    def perform(self, request, results):
        if results is None or len(results) == 0:
            return ('You must select one or more messages to Flag or Unflag them!', 'error')
        flag = self.cleaned_data['flag']
        for msg in results:
            if flag == 'flag':
                msg.flags.create()
            else:
                for msg_flag in msg.flags.all():
                    msg_flag.delete()
        return ('%d message(s) have been %sed' % (len(results), flag), 'successfully!',)

class GenderFilterForm(FilterForm):
    """ filter contacts by their gender"""

    gender = forms.ChoiceField(choices=(('', '-----'), ('M', 'Male'), ('F', 'Female'), ('None', 'N/A')),\
                               required=False)

    def filter(self, request, queryset):

        gender = self.cleaned_data['gender']
        if gender == '':
            return queryset
        elif gender == 'M':
            return queryset.filter(gender='M')
        elif gender == 'F':
            return queryset.filter(gender='F')
        else:
            return queryset.filter(gender=None)
class AgeFilterForm(FilterForm):
    """ filter contacts by their age """
    flag = forms.ChoiceField(label='' , choices=(('', '-----'), ('+=', 'Equal to'), ('>', 'Greater than'), ('<',\
                                        'Less than'), ('None', 'N/A')),required=False)
    age = forms.CharField(max_length=20, label="Age", widget=forms.TextInput(attrs={'size':'20'}),required=False)
    def filter(self, request, queryset):

        flag = self.cleaned_data['flag']
        age= int(self.cleaned_data['age'])
        end=datetime.datetime.now()
        start=end-datetime.timedelta(days=age*365)

        if flag == '':
            return queryset
        elif flag == '==':
            return queryset.filter(birthdate__year=start.year)
        elif flag == '>':
            return queryset.exclude(birthdate=None).exclude(birthdate__range=(start,end))
        elif flag=="<":
            return queryset.exclude(birthdate=None).filter(birthdate__range=(start,end))
        else:
            return queryset.filter(birthdate=None)




