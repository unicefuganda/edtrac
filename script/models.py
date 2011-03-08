from django.db import models
from poll.models import Poll
from rapidsms.models import Connection
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.conf import settings

class Script(models.Model):
    slug = models.SlugField(max_length=64, primary_key=True)
    name = models.CharField(max_length=128,
                            help_text="Human readable name.")
    sites = models.ManyToManyField(Site)
    objects = (CurrentSiteManager('sites') if settings.SITE_ID else models.Manager())    

class ScriptStep(models.Model):
    """
    Scripts are a dialogue between a user and the system, involving
    timed messages, some of which expect a response (Polls), and some
    of which don't (basic messages).  Progression through a set of script
    steps follows a set of rules, governed by the actions taken by the user
    and the time elapsed since the previous step or action.
    """
    script = models.ForeignKey(Script, related_name='steps')
    poll = models.ForeignKey(Poll, null=True)
    message = models.CharField(max_length=160)
    order = models.IntegerField()
    LENIENT = 'l'
    WAIT_MOVEON = 'w'
    WAIT_GIVEUP = 'g'
    RESEND_MOVEON = 'R'
    RESEND_GIVEUP = 'r'

    rule = models.CharField(
                max_length=1,
                choices=((LENIENT, 'Lenient (accept erroneous responses and wait for retry'),
                         (WAIT_MOVEON, 'Wait, then move to next step'),
                         (WAIT_GIVEUP, 'Wait, then stop the script for this user entirely (Giveup)'),
                         (RESEND_MOVEON, 'Resend <resend> times, then move to next step'),
                         (RESEND_GIVEUP, 'Resend <resend> times, then stop the script for this user entirely'),))
    # the number of seconds after completion of the previous step that this rule should
    # begin to take effect (i.e., a message gets sent out)
    start_offset = models.IntegerField(blank=True,null=True)

    # The time (in seconds) to wait before retrying a message
    # (in the case of RESEND_MOVEON and RESEND_GIVEUP
    # steps
    retry_offset = models.IntegerField(blank=True,null=True)

    # The time (in seconds) to wait before moving on to the
    # next step, or giving up entirely (for WAIT_MOVEON and WAIT_GIVEUP
    giveup_offset = models.IntegerField(blank=True,null=True)

    # The number of times to retry sending a question
    # for RESEND_MOVEON and RESEND_GIVEUP
    num_tries = models.IntegerField(blank=True,null=True)

class ScriptProgress(models.Model):
    # each connection should belong to only ONE script at a time,
    # and only be at ONE point in the script
    connection = models.ForeignKey(Connection, unique=True)

    script = models.ForeignKey(Script)

    # a null value here means the user just joined the script,
    # but hasn't passed even the first step
    step = models.ForeignKey(ScriptStep, null=True, blank=True)
    status = models.CharField(
                max_length=1,
                choices=(('C', 'Complete'),
                         ('P', 'In Progress'),))
    time = models.DateTimeField(auto_now=True)
    num_tries = models.IntegerField(blank=True,null=True)
