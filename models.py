import datetime

from django.db import models
from django.contrib.auth.models import User

from rapidsms.contrib.messagelog.models import Message
from rapidsms.models import Contact

# The standard template allows for any amount of whitespace at the beginning,
# followed by the alias(es) for a particular category, followed by any non-
# alphabetical character, or the end of the message
BASIC_PATTERN_TEMPLATE = '^\s*(%s)(\s|[^a-zA-Z]|$)'

# This can be configurable from settings, but here's a default list of 
# accepted yes keywords
YES_WORDS = ['yes','yeah','yep','yay','y']

# This can be configurable from settings, but here's a default list of
# accepted no keywords
NO_WORDS = ['no','nope','nah','nay','n']

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
    question = models.CharField(max_length=160)
    messages = models.ManyToManyField(Message, null=True)
    contacts = models.ManyToManyField(Contact, related_name='polls')
    user = models.ForeignKey(User)
    started = models.DateTimeField(null=True)
    type = models.CharField(
                max_length=1,
                choices=(('t', 'Text-based'),('n', 'Numeric Response')))
    
    @classmethod
    def create_yesno(cls, question, contacts, user):
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
                question=question,
                user=user,
                type='t')
        poll.contacts = contacts
        poll.categories.create(name='yes')
        poll.categories.get(name='yes').rules.create(regex=(BASIC_PATTERN_TEMPLATE % '|'.join(YES_WORDS)))
        poll.categories.create(name='no')
        poll.categories.get(name='no').rules.create(regex=(BASIC_PATTERN_TEMPLATE % '|'.join(NO_WORDS)))
        poll.categories.create(name='unknown')        
        return poll
    
    @classmethod
    def create_freeform(cls, question, contacts, user):
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
                question=question,
                user=user,
                type='t')
        poll.contacts = contacts        
        return poll
    
    @classmethod
    def create_numeric(cls, question, contacts, user):
        """
        This creates a generic numeric poll from the various parameters
        question : The question to ask when the poll is started
        contacts : a list or QuerySet of Contact objects
        user : The logged-in user creating this poll
        
        returns:
        A poll of type 'n' (Numeric)
        """        
        poll = Poll.objects.create(
                question=question,
                user=user,
                type='n')
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
        for c in self.contacts:
            # FIXME - incorporate new logger to retrieve the message id
            call_router("poll", "send_message", 
               **{"connection_id": c.default_connection().id, "text": self.question })
        self.started = datetime.datetime.now()
        self.save()

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
    
class Response(models.Model):
    """
    Responses tie incoming messages from poll participants to a particular
    bucket that their response is associated with.  Web users may also be
    able to override a particular response as belonging to a particular
    category, which shouldn't be overridden by new rules.
    """
    message = models.ForeignKey(Message)
    category = models.ForeignKey(Category, null=True)
    poll = models.ForeignKey(Poll)
    is_override = models.BooleanField(default=False)
    user = models.ForeignKey(User, null=True)
    modified = models.DateTimeField(null=True)
    value = models.DecimalField(decimal_places=10, max_digits=19, null=True)
    
class Rule(models.Model):
    """
    A rule is a regular expression that an incoming message text might
    satisfy to belong in a particular category.  A message must satisfy
    one or more rules to belong to a category.
    """
    regex = models.CharField(max_length=100)
    category = models.ForeignKey(Category, related_name='rules')
