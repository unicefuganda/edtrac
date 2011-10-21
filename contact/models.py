from django.db import models
from django.contrib.sites.managers import CurrentSiteManager
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from rapidsms_httprouter.managers import BulkInsertManager
from rapidsms_httprouter.models import Message
from rapidsms.models import Contact, Connection

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
    name = models.CharField(max_length=50, unique=True)

    def get_messages(self):
        message_flags = self.messages.values_list('message', flat=True)
        return Message.objects.filter(pk__in=message_flags)

    def __unicode__(self):
        return self.name

class MessageFlag(models.Model):
    """ relation between flag and message
    """
    message = models.ForeignKey(Message, related_name='flags')
    flag = models.ForeignKey(Flag, related_name="messages", null=True)
