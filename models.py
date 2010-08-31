from django.db import models
from django.contrib.auth.models import User

from rapidsms.contrib.messagelog.models import Message
from rapidsms.models import Contact

class Poll(models.Model):
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
        poll = Poll.objects.create(
                question=question,
                contacts=contacts,
                user=user,
                type='t')
        poll.categories.create(name='yes')
        poll.categories.create(name='no')
        return poll
    
    @classmethod
    def create_freeform(cls, question, contacts, user):
        poll = Poll.objects.create(
                question=question,
                contacts=contacts,
                user=user,
                type='t')
        return poll
    
    @classmethod
    def create_numeric(cls, question, contacts, user):
        poll = Poll.objects.create(
                question=question,
                contacts=contacts,
                user=user,
                type='n')
        return poll
    
    def start(self):
        from rapidsms.contrib.ajax.utils import call_router
        for c in self.contacts:
            call_router("poll", "send_message", 
               **{"connection_id": c.default_connection().id, "text": self.question })
        self.started = datetime.datetime.now()
        self.save()

class Category(models.Model):
    name = models.CharField(max_length=50)
    poll = models.ForeignKey(Poll, related_name='categories')
    
class Response(models.Model):
    message = models.ForeignKey(Message)
    category = models.ForeignKey(Category)
    poll = models.ForeignKey(Poll)
    is_override = models.BooleanField(default=False)
    user = models.ForeignKey(User, null=True)
    modified = models.DateTimeField(null=True)
    value = models.DecimalField(decimal_places=10, max_digits=19, null=True)
    
class Rule(models.Model):
    regex = models.CharField(max_length=100)
    category = models.ForeignKey(Category, related_name='rules')
