import datetime

from django.db import models
from django.contrib.auth.models import User

from rapidsms.contrib.messagelog.models import Message
from rapidsms.models import Contact

from eav import register

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
    
    FIXME: probably need a short description field?
    FIXME: contact groups, if implemented in core or contrib, should be used here,
           instead of a many-to-many field
    """
    
    TYPE_TEXT = 't'
    TYPE_NUMERIC = 'n'
        
    name = models.CharField(max_length=32,
                            help_text="Human readable name.")
    question = models.CharField(max_length=160)
    messages = models.ManyToManyField(Message, null=True)
    contacts = models.ManyToManyField(Contact, related_name='polls')
    user = models.ForeignKey(User)
    started = models.DateTimeField(null=True)
    type = models.CharField(
                max_length=1,
                choices=((TYPE_TEXT, 'Text-based'),(TYPE_NUMERIC, 'Numeric Response')))
    default_response = models.CharField(max_length=160)
    
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
        poll.categories.create(name='unknown', default=True)
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
    
    def start(self):
        """
        This starts the poll: outgoing messages are sent to all the contacts
        registered with this poll, and the start date is updated accordingly.
        All incoming messages from these users will be considered as
        potentially a response to this poll.
        """
        from rapidsms.contrib.ajax.utils import call_router
        for c in self.contacts.all():
            # FIXME - incorporate new logger to retrieve the message id
#            call_router("poll", "send", 
#               **{"identity": c.default_connection.identity, "text": self.question })
            pass
        self.started = datetime.datetime.now()
        self.save()
    
    def reprocess_responses(self):
        for rc in ResponseCategory.objects.filter(category__poll=self, is_override=False):
            rc.delete()

        for resp in Response.objects.filter(poll=self):
            for category in self.categories.all():
                for rule in category.rules.all():
                    regex = re.compile(rule.regex)
                    print resp.eav.poll_text_value
                    if regex.search(resp.eav.poll_text_value) and not resp.categories.filter(category=category).count():
                        rc = ResponseCategory.objects.create(response = resp, category=category)
                        break
            if not resp.categories.all().count() and self.categories.filter(default=True).count():
                resp.categories.add(ResponseCategory.objects.create(response = resp, category=self.categories.get(default=True)))
    
    def process_response(self, message):
        # FIXME - incorporate new logger to retrieve incoming message id
        resp = Response.objects.create(poll=self)
        outgoing_message = self.default_response
        if (self.type == Poll.TYPE_NUMERIC):
            try:
                resp.eav.poll_number_value = float(message.text)
            except ValueError:        
                pass
        elif (self.type == Poll.TYPE_TEXT):
            resp.eav.poll_text_value = message.text
            if self.categories:
                for category in self.categories.all():
                    for rule in category.rules.all():
                        regex = re.compile(rule.regex)
                        if regex.search(message.text):
                            rc = ResponseCategory.objects.create(response = resp, category=category)
                            resp.categories.add(rc)
                            break
            if not resp.categories.all().count() and self.categories.filter(default=True).count():
                resp.categories.add(ResponseCategory.objects.create(response = resp, category=self.categories.get(default=True)))
            
            for respcategory in resp.categories.order_by('category__priority'):
                if respcategory.category.response:
                    outgoing_message = respcategory.category.response
                    break
        resp.save()
        if not outgoing_message:
            return "We have received your response, thank you!"
        else:
            return outgoing_message

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
    
    @classmethod
    def clear_defaults(cls, poll):
        for c in Category.objects.filter(poll=poll, default=True):
            c.default=False
            c.save()        
    
class Response(models.Model):
    """
    Responses tie incoming messages from poll participants to a particular
    bucket that their response is associated with.  Web users may also be
    able to override a particular response as belonging to a particular
    category, which shouldn't be overridden by new rules.
    """
    message = models.ForeignKey(Message, null=True)
    poll = models.ForeignKey(Poll, related_name='responses')

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
