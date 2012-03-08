from django.db import models
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from rapidsms_httprouter.managers import BulkInsertManager
from rapidsms_httprouter.models import Message
from rapidsms.models import Contact, Connection
import re

c_bulk_mgr = BulkInsertManager()
c_bulk_mgr.contribute_to_class(Contact, 'bulk')

cn_bulk_mgr = BulkInsertManager()
cn_bulk_mgr.contribute_to_class(Connection, 'bulk')

class MassText(models.Model):
    sites = models.ManyToManyField(Site)
    contacts = models.ManyToManyField(Contact, related_name='masstexts')
    user = models.ForeignKey(User)
    date = models.DateTimeField(auto_now_add=True, null=True)
    text = models.TextField()
    objects = models.Manager()
    on_site = CurrentSiteManager('sites')
    bulk = BulkInsertManager()

    class Meta:
        permissions = (
            ("can_message", "Can send messages, create polls, etc"),
        )

class Flag(models.Model):
    """
    a Message flag
    """
    contains_all_of=1
    contains_one_of=2

    name = models.CharField(max_length=50, unique=True)
    words=models.CharField(max_length=200,null=True)
    rule=models.IntegerField(max_length=10,choices=((contains_all_of,"contains_all_of"),(contains_one_of,"contains_one_of"),),null=True)
    rule_regex=models.CharField(max_length=200,null=True)

    def get_messages(self):
        message_flags = self.messages.values_list('message', flat=True)
        return Message.objects.filter(pk__in=message_flags)

    def get_regex(self):
        words=self.words.replace(','," ").split()

        if self.rule == 1:
            all_template=r"(?=.*\b%s\b)"
            w_regex=r""
            for word in words:
                w_regex=w_regex+all_template%re.escape(word)
            return w_regex

        elif self.rule == 2:
            one_template=r"(\b%s\b)"
            w_regex=r""
            for word in words:
                w_regex=w_regex+r"|"+one_template%re.escape(word)
            rule=w_regex

    def save(self,*args,**kwargs):
        if self.words:
            self.rule_regex = self.get_regex()
        super(Flag,self).save()

    def __unicode__(self):
        return self.name

class MessageFlag(models.Model):
    """ relation between flag and message
    """
    message = models.ForeignKey(Message, related_name='flags')
    flag = models.ForeignKey(Flag, related_name="messages", null=True)
    
    def flags(self):
        mf=MessageFlag.objects.filter(message=self.message).values_list("flag",flat=True)
        return Flag.objects.filter(pk__in=mf)
