import datetime
import difflib

from code_generator.code_generator import generate_tracking_tag

from django.db import models
from django.db.models import Sum, Avg, Q
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django import forms
from mptt.forms import TreeNodeChoiceField
from rapidsms.models import Contact, Connection

from eav import register
from eav.models import Value, Attribute

from .utils import init_attributes

from simple_locations.models import Area

from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import get_router

from rapidsms.messages.outgoing import OutgoingMessage
from django.conf import settings
from django.db.models.signals import post_syncdb
import re

# The standard template allows for any amount of whitespace at the beginning,
# followed by the alias(es) for a particular category, followed by any non-
# alphabetical character, or the end of the message
STARTSWITH_PATTERN_TEMPLATE = '^\s*(%s)(\s|[^a-zA-Z]|$)'

CONTAINS_PATTERN_TEMPLATE = '^.*\s*(%s)(\s|[^a-zA-Z]|$)'

# This can be configurable from settings, but here's a default list of 
# accepted yes keywords
YES_WORDS = ['yes','yeah','yep','yay','y']

# This can be configurable from settings, but here's a default list of
# accepted no keywords
NO_WORDS = ['no','nope','nah','nay','n']

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
                 level_indicator=u'.', required=True)

class NameResponseForm(ResponseForm):
    value = forms.CharField()

class ResponseCategory(models.Model):
    category = models.ForeignKey('Category')
    response = models.ForeignKey('Response', related_name='categories')
    is_override = models.BooleanField(default=False)
    user = models.ForeignKey(User, null=True)

class Poll(models.Model):
    """
    Polls represent a simple-question, simple-response communication modality
    via SMS.  They can be thought of as a similar to a single datum in an XForm,
    although for now the only data types available are yes/no, free-form text, and
    numeric response.  Fairly simple idea, a poll is created, containing a question 
    (the outgoing messages), a list of contacts (those to poll) and an expected
    *type* of response.  The poll can be edited, contact lists modified, etc. via
    the web (the "user"), until it is eventually *started.*  When a poll is started,
    the outgoing question will be sent to all contacts, and any subsequent messages
    coming in from the contacts associated with this poll (until they are polled again)
    will be parsed (or attempted to be parsed) by this poll, and bucketed into a 
    particular category.
    
    FIXME: contact groups, if implemented in core or contrib, should be used here,
           instead of a many-to-many field
    """
    
    TYPE_TEXT = 't'
    TYPE_NUMERIC = 'n'
    TYPE_LOCATION = 'l'
    TYPE_REGISTRATION = 'r'

    TYPE_CHOICES = {
        TYPE_LOCATION: dict(
                        label='Location-based',
                        type=TYPE_LOCATION,
                        db_type=Attribute.TYPE_OBJECT,
                        parser=None,
                        view_template='polls/response_location_view.html',
                        edit_template='polls/response_location_edit.html',
                        report_columns=(('Text','text'),('Location','location'),('Categories','categories')),
                        edit_form=LocationResponseForm),
        TYPE_NUMERIC: dict(
                        label='Numeric Response',
                        type=TYPE_NUMERIC,
                        db_type=Attribute.TYPE_FLOAT,
                        parser=None,
                        view_template='polls/response_numeric_view.html',
                        edit_template='polls/response_numeric_edit.html',
                        report_columns=(('Text','text'),('Value','value'), ('Categories', 'categories')),
                        edit_form=NumericResponseForm),
        TYPE_TEXT:  dict(
                        label='Free-form',
                        type=TYPE_TEXT,
                        db_type=Attribute.TYPE_TEXT,
                        parser=None,
                        view_template='polls/response_text_view.html',
                        edit_template='polls/response_text_edit.html',
                        report_columns=(('Text', 'text'),('Categories','categories')),
                        edit_form=ResponseForm),
        TYPE_REGISTRATION:  dict(
                        label='Name/registration-based',
                        type=TYPE_REGISTRATION,
                        db_type=Attribute.TYPE_TEXT,
                        parser=None,
                        view_template='polls/response_registration_view.html',
                        edit_template='polls/response_registration_edit.html',
                        report_columns=(('Text','text'),('Categories','categories')),
                        edit_form=NameResponseForm),
    }

    name = models.CharField(max_length=32,
                            help_text="Human readable name.")
    question = models.CharField(max_length=160)
    messages = models.ManyToManyField(Message, null=True)
    contacts = models.ManyToManyField(Contact, related_name='polls')
    user = models.ForeignKey(User)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    type = models.SlugField(max_length=8, null=True, blank=True)
    type = models.CharField(
                max_length=1,
                choices=((TYPE_TEXT, 'Text-based'),(TYPE_NUMERIC, 'Numeric Response')))
    default_response = models.CharField(max_length=160)
    sites = models.ManyToManyField(Site)
    objects = (CurrentSiteManager('sites') if settings.SITE_ID else models.Manager())

    class Meta:
        permissions = (
            ("can_poll", "Can send polls"),
            ("can_edit_poll", "Can edit poll rules, categories, and responses"),
        )

    @classmethod
    def register_poll_type(cls, field_type, label, parserFunc, \
                           db_type=TYPE_TEXT, \
                           view_template=None,\
                           edit_template=None,\
                           report_columns=None,\
                           edit_form=None):
        """
        Used to register a new question type for Polls.  You can use this method to build new question types that are
        available when building Polls.  These types may just do custom parsing of the SMS text sent in, then stuff
        those results in a normal core datatype, or they may lookup and reference completely custom attributes.

        Arguments are:
           label:       The label used for this field type in the user interface
           field_type:  A slug to identify this field type, must be unique across all field types
           parser:      The function called to turn the raw string into the appropriate type, should take one argument:
                        'value' the string value submitted.
           db_type:     How the value will be stored in the database, can be one of: TYPE_FLOAT, TYPE_TEXT or TYPE_OBJECT
                        (defaults to TYPE_TEXT)
           [view_template]: A template that renders an individual row in a table displaying responses
           [edit_template]: A template that renders an individual row for editing a response
           [report_columns]: the column labels for a table of responses for a poll of a particular type
           [edit_form]: A custom edit form for editing responses
        """
        # set the defaults
        if view_template is None:
            view_template = 'polls/response_custom_view.html'
        if edit_template is None:
            edit_template = 'polls/response_custom_edit.html'
        if report_columns is None:
            report_columns = (('Original Text','text'),('Value','custom'))

        Poll.TYPE_CHOICES[field_type] = dict(
            type=field_type, label=label,
            db_type=db_type, parser=parserFunc,
            view_template=view_template,
            edit_template=edit_template,
            report_columns=report_columns,
            edit_form=edit_form)

    @classmethod
    def create_yesno(cls, name, question, default_response, contacts, user):
        """
        This creates a generic yes/no poll from the various parameters
        question : The question to ask when the poll is started
        contacts : a list or QuerySet of Contact objects
        user : The logged-in user creating this poll
        
        returns:
        A poll of type 't' (Text-based) with two categories, 'yes', and 'no',
        that allow basic responses starting with yes, no, or other aliases
        """
        poll = Poll.objects.create(
                name=name,
                question=question,
                default_response=default_response,
                user=user,
                type=Poll.TYPE_TEXT)
        poll.contacts = contacts
        poll.categories.create(name='yes')
        poll.categories.get(name='yes').rules.create(
            regex=(STARTSWITH_PATTERN_TEMPLATE % '|'.join(YES_WORDS)),
            rule_type=Rule.TYPE_REGEX,
            rule_string=(STARTSWITH_PATTERN_TEMPLATE % '|'.join(YES_WORDS)))
        poll.categories.create(name='no')
        poll.categories.get(name='no').rules.create(
            regex=(STARTSWITH_PATTERN_TEMPLATE % '|'.join(NO_WORDS)),
            rule_type=Rule.TYPE_REGEX,
            rule_string=(STARTSWITH_PATTERN_TEMPLATE % '|'.join(NO_WORDS)))
        poll.categories.create(name='unknown', default=True, error_category=True)
        return poll
    
    @classmethod
    def create_freeform(cls, name, question, default_response, contacts, user):
        """
        This creates a generic text-based poll from the various parameters
        question : The question to ask when the poll is started
        contacts : a list or QuerySet of Contact objects
        user : The logged-in user creating this poll
        
        returns:
        A poll of type 't' (Text-based) with no categories (the user can
        add them ad hoc as responses come in)
        """        
        poll = Poll.objects.create(
                name=name,
                question=question,
                default_response=default_response,                
                user=user,
                type=Poll.TYPE_TEXT)
        poll.contacts = contacts        
        return poll

    @classmethod
    def create_registration(cls, name, question, default_response, contacts, user):
        """
        This creates a generic text-based poll from the various parameters,
        but will allow the user to decide, after the results come in, whether or
        not to apply responses to the associated contact's name.
        question : The question to ask when the poll is started
        contacts : a list or QuerySet of Contact objects
        user : The logged-in user creating this poll
        
        returns:
        A poll of type 'r' (Registration-based) with no categories (the user can
        add them ad hoc as responses come in)
        """
        poll = Poll.objects.create(
                name=name,
                question=question,
                default_response=default_response,                
                user=user,
                type=Poll.TYPE_REGISTRATION)
        poll.contacts = contacts        
        return poll
    
    @classmethod
    def create_numeric(cls, name, question, default_response, contacts, user):
        """
        This creates a generic numeric poll from the various parameters
        question : The question to ask when the poll is started
        contacts : a list or QuerySet of Contact objects
        user : The logged-in user creating this poll
        
        returns:
        A poll of type 'n' (Numeric)
        """
        poll = Poll.objects.create(
                name=name,
                question=question,
                default_response=default_response,                
                user=user,
                type=Poll.TYPE_NUMERIC)
        poll.contacts = contacts
        return poll
    
    @classmethod
    def create_location_based(cls, name, question, default_response, contacts, user):
        """
        This creates a generic text-based poll from the various parameters,
        but will attempt to match incoming messages to a location already in
        the system, or create new locations as they arrive.
        question : The question to ask when the poll is started
        contacts : a list or QuerySet of Contact objects
        user : The logged-in user creating this poll
        
        returns:
        A poll of type 'l' (Location-based) with no categories (the user can
        add them ad hoc as responses come in)
        """        
        poll = Poll.objects.create(
                name=name,
                question=question,
                default_response=default_response,                
                user=user,
                type=Poll.TYPE_LOCATION)
        poll.contacts = contacts
        return poll

    @classmethod
    def create_custom(cls, type, name, question, default_response, contacts, user):
        """
        This creates a poll of custom type from the various parameters.
        question : The question to ask when the poll is started
        contacts : a list or QuerySet of Contact objects
        user : The logged-in user creating this poll

        returns:
        A poll of custom type with no categories (the user can
        add them ad hoc as responses come in)
        """
        poll = Poll.objects.create(
                name=name,
                question=question,
                default_response=default_response,
                user=user,
                type=type)
        poll.contacts = contacts
        return poll

    def start(self):
        """
        This starts the poll: outgoing messages are sent to all the contacts
        registered with this poll, and the start date is updated accordingly.
        All incoming messages from these users will be considered as
        potentially a response to this poll.
        """
        self.start_date = datetime.datetime.now()
        self.save()
        router = get_router()
        for contact in self.contacts.all():
            for connection in Connection.objects.filter(contact=contact):
                outgoing = OutgoingMessage(connection, self.question)
                outgoing_obj = router.handle_outgoing(outgoing)
                if outgoing_obj:
                    self.messages.add(outgoing_obj)

            pass
    
    def end(self):
        self.end_date = datetime.datetime.now()
        self.save()
    
    def reprocess_responses(self):
        for rc in ResponseCategory.objects.filter(category__poll=self, is_override=False):
            rc.delete()

        for resp in Response.objects.filter(poll=self):
            resp.has_errors = False
            for category in self.categories.all():
                for rule in category.rules.all():
                    regex = re.compile(rule.regex)
                    if resp.eav.poll_text_value:
                        if regex.search(resp.eav.poll_text_value.lower()) and not resp.categories.filter(category=category).count():
                            if category.error_category:
                                resp.has_errors = True
                            rc = ResponseCategory.objects.create(response = resp, category=category)
                            break
            if not resp.categories.all().count() and self.categories.filter(default=True).count():
                if self.categories.get(default=True).error_category:
                    resp.has_errors = True
                resp.categories.add(ResponseCategory.objects.create(response = resp, category=self.categories.get(default=True)))
            resp.save()
    
    def process_response(self, message):
        db_message = None
        if hasattr(message, 'db_message'):
            db_message = message.db_message
        resp = Response.objects.create(poll=self, message=db_message, contact=db_message.connection.contact, date=db_message.date)
        outgoing_message = self.default_response
        if (self.type == Poll.TYPE_LOCATION):
            location_template = STARTSWITH_PATTERN_TEMPLATE % '[a-zA-Z]*'
            regex = re.compile(location_template)
            if regex.search(message.text):
                spn = regex.search(message.text).span()
                location_str = message.text[spn[0]:spn[1]]
                area = None
                area_names = Area.objects.all().values_list('name', flat=True)
                area_names_lower = [ai.lower() for ai in area_names]
                area_names_matches = difflib.get_close_matches(location_str.lower(), area_names_lower)
                if area_names_matches:
                    area = Area.objects.filter(name__iexact=area_names_matches[0])[0]
                else:
                    area = Area.objects.create(name=location_str, code=generate_tracking_tag())
                resp.eav.poll_location_value = area
            else:
                resp.has_errors = True
                
        elif (self.type == Poll.TYPE_NUMERIC):
            try:
                resp.eav.poll_number_value = float(message.text)
            except ValueError:
                resp.has_errors = True
            
        elif ((self.type == Poll.TYPE_TEXT) or (self.type == Poll.TYPE_REGISTRATION)):
            resp.eav.poll_text_value = message.text
            if self.categories:
                for category in self.categories.all():
                    for rule in category.rules.all():
                        regex = re.compile(rule.regex)
                        if regex.search(message.text.lower()):
                            rc = ResponseCategory.objects.create(response = resp, category=category)
                            resp.categories.add(rc)
                            if category.error_category:
                                resp.has_errors = True
                                outgoing_message = category.response
                            break

        elif self.type in Poll.TYPE_CHOICES:
            typedef = Poll.TYPE_CHOICES[self.type]
            try:
                cleaned_value = typedef['parser'](message.text)
                if typedef['db_type'] == Attribute.TYPE_TEXT:
                    resp.eav.poll_text_value = cleaned_value
                elif typedef['db_type'] == Attribute.TYPE_FLOAT:
                    resp.eav.poll_number_value = cleaned_value
                elif typedef['db_type'] == Attribute.TYPE_OBJECT:
                    resp.eav.poll_location_value = cleaned_value
            except ValidationError as e:
                resp.has_errors = True
                if getattr(e, 'messages', None):
                    outgoing_message = str(e.messages[0])
                else:
                    outgoing_message = None

        if not resp.categories.all().count() and self.categories.filter(default=True).count():
            resp.categories.add(ResponseCategory.objects.create(response = resp, category=self.categories.get(default=True)))
            if self.categories.get(default=True).error_category:
                resp.has_errors = True
                outgoing_message = self.categories.get(default=True).response

        if (not resp.has_errors or not outgoing_message):
            for respcategory in resp.categories.order_by('category__priority'):
                if respcategory.category.response:
                    outgoing_message = respcategory.category.response
                    break
        resp.save()
        if not outgoing_message:
            return (resp, None,)
        else:
            return (resp,outgoing_message,)

    def get_generic_report_data(self):
        context = {}
        context['total_responses'] = Response.objects.filter(poll=self).count()
        context['response_rate'] = (float(len(Response.objects.filter(poll=self).values_list('contact', flat=True).distinct())) / self.contacts.count()) * 100
        return context

    def get_text_report_data(self, location_id=None):
        context = {}
        sublocations = []
        if location_id:
            sublocations = location_id.get_descendants()
        context['total_responses'] = Response.objects.filter(poll=self).filter(Q(contact__reporting_location=location_id) | Q(contact__reporting_location__in=sublocations)).count()
        context['response_rate'] = (float(len(Response.objects.filter(poll=self).filter(Q(contact__reporting_location=location_id) | Q(contact__reporting_location__in=sublocations)).values_list('contact', flat=True).distinct())) / self.contacts.count()) * 100
        context['report_data'] = []
        for c in self.categories.all():
            category_responses = Response.objects.filter(categories__category=c).filter(Q(contact__reporting_location=location_id) | Q(contact__reporting_location__in=sublocations)).count()
            category_percentage = 0
            if context['total_responses']:
                category_percentage = (float(category_responses) / float(context['total_responses'])) * 100.0
            context['report_data'].append((c, category_responses, category_percentage))
        context['uncategorized'] = Response.objects.filter(poll=self).filter(Q(contact__reporting_location=location_id) | Q(contact__reporting_location__in=sublocations)).exclude(categories__in=ResponseCategory.objects.filter(category__poll=self)).count()
        context['uncategorized_percent'] = 0
        if context['total_responses']:
            context['uncategorized_percent'] = (float(context['uncategorized']) / float(context['total_responses'])) * 100.0 
        return context

    def get_numeric_report_data(self, location_id=None):
        context = {}
        sublocations = []
        if location_id:
            sublocations = location_id.get_descendants()
        context['total_responses'] = Response.objects.filter(poll=self).filter(Q(contact__reporting_location=location_id) | Q(contact__reporting_location__in=sublocations)).count()
        context['response_rate'] = (float(len(Response.objects.filter(poll=self).filter(Q(contact__reporting_location=location_id) | Q(contact__reporting_location__in=sublocations)).values_list('contact', flat=True).distinct())) / self.contacts.count()) * 100
        responses = Response.objects.filter(poll=self).filter(Q(contact__reporting_location=location_id) | Q(contact__reporting_location__in=sublocations))
        vals = Value.objects.filter(entity_id__in=responses).values_list('value_float',flat=True)
        context['total'] = sum(vals)
        context['average'] = float(context['total']) / float(len(vals))
        mode_dict = {}
        mode = None
        for v in vals:
            if v in mode_dict:
                mode_dict[v] = mode_dict[v] + 1
            else:
                mode_dict[v] = 1
                if not mode:
                    mode = v
            if mode_dict[v] > mode_dict[mode]:
                mode = v
        context['mode'] = mode
        return context
    
    def __unicode__(self):
        return self.name


class Category(models.Model):
    """
    A category is a 'bucket' that an incoming poll response is placed into.
    
    Categories have rules, which are regular expressions that a message must
    satisfy to belong to a particular category (otherwise a response will have
    None for its category). FIXME does this make sense, or should all polls
    have a default 'unknown' category?
    """
    name = models.CharField(max_length=50)
    poll = models.ForeignKey(Poll, related_name='categories')
    priority = models.PositiveSmallIntegerField(null=True)
    color = models.CharField(max_length=6)
    default = models.BooleanField(default=False)
    response = models.CharField(max_length=160, null=True)
    error_category = models.BooleanField(default=False)
    
    @classmethod
    def clear_defaults(cls, poll):
        for c in Category.objects.filter(poll=poll, default=True):
            c.default=False
            c.save()
    
    def __unicode__(self):
        return u'%s' % self.name  
    
class Response(models.Model):
    """
    Responses tie incoming messages from poll participants to a particular
    bucket that their response is associated with.  Web users may also be
    able to override a particular response as belonging to a particular
    category, which shouldn't be overridden by new rules.
    """
    message = models.ForeignKey(Message, null=True, related_name='poll_responses')
    poll    = models.ForeignKey(Poll, related_name='responses')
    contact = models.ForeignKey(Contact, null=True, blank=True, related_name='responses')
    date    = models.DateTimeField(auto_now_add=True)
    has_errors = models.BooleanField(default=False)

    def update_categories(self, categories, user):
        for c in categories:
            if not self.categories.filter(category=c).count():
                ResponseCategory.objects.create(response=self, category=c, is_override=True, user=user)
        for rc in self.categories.all():
            if not rc.category in categories:
                rc.delete()    

register(Response)

class Rule(models.Model):
    """
    A rule is a regular expression that an incoming message text might
    satisfy to belong in a particular category.  A message must satisfy
    one or more rules to belong to a category.
    """
    
    TYPE_STARTSWITH = 'sw'
    TYPE_CONTAINS = 'c'
    TYPE_REGEX = 'r'
    RULE_CHOICES = (
         (TYPE_STARTSWITH, 'Starts With'),
         (TYPE_CONTAINS, 'Contains'),
         (TYPE_REGEX, 'Regex (advanced)'))
    
    RULE_DICTIONARY = {
         TYPE_STARTSWITH: 'Starts With',
         TYPE_CONTAINS: 'Contains',
         TYPE_REGEX: 'Regex (advanced)',        
    }
    
    regex = models.CharField(max_length=256)
    category = models.ForeignKey(Category, related_name='rules')
    rule_type = models.CharField(max_length=2,  choices=RULE_CHOICES)
    rule_string = models.CharField(max_length=256, null=True)
    
    @property
    def rule_type_friendly(self):
        return Rule.RULE_DICTIONARY[self.rule_type]
    
    def update_regex(self): 
        if self.rule_type == Rule.TYPE_STARTSWITH:
            self.regex = STARTSWITH_PATTERN_TEMPLATE % self.rule_string
        elif self.rule_type == Rule.TYPE_CONTAINS:
            self.regex = CONTAINS_PATTERN_TEMPLATE % self.rule_string
        elif self.rule_type == Rule.TYPE_REGEX:
            self.regex = self.rule_string

post_syncdb.connect(init_attributes, weak=True)