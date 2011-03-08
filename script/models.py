from django.db import models
from poll.models import Poll
from rapidsms.models import Connection
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.conf import settings

class ScriptStep(models.Model):
    """
    Scripts are a dialogue between a user and the system, involving
    timed messages, some of which expect a response (Polls), and some
    of which don't (basic messages).  Progression through a set of script
    steps follows a set of rules, governed by the actions taken by the user
    and the time elapsed since the previous step or action.
    """
    slug = models.SlugField(max_length=64, primary_key=True)
    name = models.CharField(max_length=128,
                            help_text="Human readable name.")
    poll = models.ForeignKey(Poll, null=True)
    message = models.CharField(max_length=160)
    rule = models.CharField(
                max_length=1,
                choices=(('l', 'Lenient (accept erroneous responses and wait for retry'),
                         ('w', 'Wait, then move to next step'),
                         ('g', 'Wait, then stop the script for this user entirely (Giveup)'),
                         ('R', 'Resend <resend> times, then move to next step'),
                         ('r', 'Resend <resend> times, then stop the script for this user entirely'),))
    start_offset = models.IntegerField(blank=True,null=True)
    retry_offset = models.IntegerField(blank=True,null=True)
    giveup_offset = models.IntegerField(blank=True,null=True)
    num_tries = models.IntegerField(blank=True,null=True)
    sites = models.ManyToManyField(Site)
    objects = (CurrentSiteManager('sites') if settings.SITE_ID else models.Manager())

class ScriptProgress(models.Model):
    connection = models.ForeignKey(Connection, unique=True)
    script_step = models.ForeignKey(ScriptStep)
    status = models.CharField(
                max_length=1,
                choices=(('C', 'Complete'),
                         ('P', 'In Progress'),))
    time = models.DateTimeField(auto_now=True)
    num_tries = models.IntegerField(blank=True,null=True)
