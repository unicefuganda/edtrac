import datetime
from django.db import models
from poll.models import Poll,Response
from rapidsms.models import Connection
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.conf import settings
from script.signals import script_progress
from django.db.models.signals import post_save
from rapidsms.messages.incoming import IncomingMessage
import difflib
class Script(models.Model):
    slug = models.SlugField(max_length=64, primary_key=True)
    name = models.CharField(max_length=128,
                            help_text="Human readable name.")
    sites = models.ManyToManyField(Site)
    objects = (CurrentSiteManager('sites') if settings.SITE_ID else models.Manager())    
    def __unicode__(self):
        return "%s"%self.name

class ScriptStep(models.Model):
    """
    Scripts are a dialogue between a user and the system, involving
    timed messages, some of which expect a response (Polls), and some
    of which don't (basic messages).  Progression through a set of script
    steps follows a set of rules, governed by the actions taken by the user
    and the time elapsed since the previous step or action.
    """
    script = models.ForeignKey(Script, related_name='steps')
    poll = models.ForeignKey(Poll, null=True, blank=True)
    message = models.CharField(max_length=160,blank=True)
    order = models.IntegerField()
    LENIENT = 'l'
    STRICT = 's'
    WAIT_MOVEON = 'w'
    WAIT_GIVEUP = 'g'
    RESEND_MOVEON = 'R'
    RESEND_GIVEUP = 'r'

    rule = models.CharField(
                max_length=1,
                choices=((LENIENT, 'Lenient (accept erroneous responses and move on to the next step)'),
                         (STRICT, 'Strict (wait until the user submits a valid response with no errors)'),
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

    def __unicode__(self):
        return "%d"%self.order


class ScriptProgress(models.Model):
    # each connection should belong to only ONE script at a time,
    # and only be at ONE point in the script
    connection = models.ForeignKey(Connection, unique=True)

    script = models.ForeignKey(Script)

    # a null value here means the user just joined the script,
    # but hasn't passed even the first step
    step = models.ForeignKey(ScriptStep, null=True, blank=True)
    COMPLETE = 'C'
    PENDING = 'P'
    status = models.CharField(
                max_length=1,
                choices=((COMPLETE, 'Complete'),
                         (PENDING, 'In Progress'),))
    time = models.DateTimeField(auto_now=True)
    num_tries = models.IntegerField(blank=True,null=True)

    def __unicode__(self):
        if self.step:
            return "%d"%self.step.order
        else:
            return "Not Started"

    def get_next_step(self):
        if self.step==self.get_last_step():
            return None
        else:
            try:
                steps_list=list(self.script.steps.order_by('order').values_list('order', flat=True))
                next_step=steps_list[steps_list.index(self.step.order)+1]

            except IndexError:
                return None
            return self.script.steps.get(order=next_step)

    def get_initial_step(self):
        try:
            return self.script.steps.order_by('order')[0]
        except IndexError:
            return None
    def get_last_step(self):
        try:
            return self.script.steps.order_by('-order')[0]
        except IndexError:
            return None
#    should we retry the current step now?
    def retry_now(self):
        if self.step.retry_offset:
            retry_time = self.time + datetime.timedelta(seconds=self.step.retry_offset)
            if retry_time and retry_time >= datetime.datetime.now():
                return True
            else:
                return False
        else:
            return True
    
#    should we move on to the next step now?
    def proceed(self):
        next_step = self.get_next_step()
        if next_step.start_offset:
            start_time = self.time + datetime.timedelta(seconds=next_step.start_offset)
            if start_time and start_time >= datetime.datetime.now():
                return True
            else:
                return False
        else:
            return True

#    should we give up now?
    def give_up_now(self):
        if self.step.giveup_offset:
            give_up_time = self.time + datetime.timedelta(seconds=self.step.giveup_offset)
            if give_up_time and give_up_time >= datetime.datetime.now():
                return True
            else:
                return False
        else:
            return True

#    should we keep retrying the current step?
    def keep_retrying(self):
        if self.step.num_tries and self.num_tries < self.step.num_tries:
            return True
        else:
            False

    def fire_pre_transition_signal(self):
        script_progress_pre_change.send(sender=self, connection=self.connection,steps_list=self.step)
    def fire_post_transition_signal(self):
        script_progress.send(sender=self, connection=self.connection,steps_list=self.step)
    def fire_script_completed_signal(self):
        fire_script_completed_signal(sender=self, connection=self.connection)
class ScriptSession(models.Model):
    connection=models.ForeignKey(Connection, unique=True)
    script=models.ForeignKey(Script)
    start_time=models.DateTimeField(auto_now=True)
    end_time=models.DateTimeField()

    def get_step(self):
        return ScriptProgress.objects.get(connection=self.connection)
    """get all the script session objects for each connection """
    def get_audit_trail(connection):
        return ScriptSession.objects.filter(connection=connection)


class ScriptResponse(models.Model):
    session=models.ForeignKey(ScriptSession,related_name='responses')
    response=models.ForeignKey(Response)



    
