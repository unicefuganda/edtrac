import datetime
from django.db import models
from poll.models import Poll, Response
from rapidsms.models import Connection
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.conf import settings
from django.db import connection
from script.signals import *
from .managers import ProgressManager,ScriptProgressQuerySet
from rapidsms.messages.incoming import IncomingMessage
import difflib
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template import Context, Template

class Script(models.Model):
    slug = models.SlugField(max_length=64, primary_key=True)
    name = models.CharField(max_length=128,
                            help_text="Human readable name.")
    sites = models.ManyToManyField(Site)
    objects = models.Manager()
    on_site = CurrentSiteManager('sites')
    enabled = models.BooleanField(default=True)
    def __unicode__(self):
        return "%s" % self.name


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
    message = models.CharField(max_length=160, blank=True)
    email = models.ForeignKey('Email', null=True, blank=True)
    order = models.IntegerField()
    LENIENT = 'l'
    STRICT = 's'
    STRICT_MOVEON = 'M'
    STRICT_GIVEUP = 'S'
    WAIT_MOVEON = 'w'
    WAIT_GIVEUP = 'g'
    RESEND_MOVEON = 'R'
    RESEND_GIVEUP = 'r'

    rule = models.CharField(
                max_length=1,
                choices=((LENIENT, 'Lenient (accept erroneous responses and move on to the next step)'),
                         (STRICT, 'Strict (wait until the user submits a valid response with no errors)'),
                         (STRICT_MOVEON, 'Strict tries (give the user n tries to send a valid response with no errors, resend the question n times if no response, then move on to the next step)'),
                         (STRICT_GIVEUP, 'Strict tries (give the user n tries to send a valid response with no errors, resend the question n times if no response, then give up )'),
                         (WAIT_MOVEON, 'Wait for <giveup_offset> seconds, then move to next step'),
                         (WAIT_GIVEUP, 'Wait for <giveup_offset> seconds, then stop the script for this user entirely'),
                         (RESEND_MOVEON, 'Resend message/question <num_tries> times, then move to next step'),
                         (RESEND_GIVEUP, 'Resend message/question <num_tries> times, then stop the script for this user entirely'),))
    # the number of seconds after completion of the previous step that this rule should
    # begin to take effect (i.e., a message gets sent out)
    start_offset = models.IntegerField(blank=True, null=True)

    # The time (in seconds) to wait before retrying a message
    # (in the case of RESEND_MOVEON and RESEND_GIVEUP
    # steps
    retry_offset = models.IntegerField(blank=True, null=True)

    # The time (in seconds) to wait before moving on to the
    # next step, or giving up entirely (for WAIT_MOVEON and WAIT_GIVEUP)
    giveup_offset = models.IntegerField(blank=True, null=True)

    # The number of times to retry sending a question
    # for RESEND_MOVEON and RESEND_GIVEUP
    num_tries = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return "%d" % self.order


class ScriptProgress(models.Model):
    """
    This model keeps track of any Connections actively involved in a
    script currently, including the last time there was an interaction,
    the current step the user has progressed to, and the
    number of times a message has been resent (if any).  This only keeps
    actively-running script participants and their current progress,
    the full list of responses sent by a user is tracked elsewhere,
    and upon script completion the Connection is deleted from this table.
    """
    # each connection should belong to only ONE script at a time,
    # and only be at ONE point in the script.  However, due to
    # the convenience of queueing up several scripts known not
    # to clash, you can add as many as you want
    connection = models.ForeignKey(Connection)

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
    time = models.DateTimeField(default=datetime.datetime.now)
    num_tries = models.IntegerField(blank=True, null=True)
    language = models.CharField(max_length=5, choices=settings.LANGUAGES, null=True)

    objects = ProgressManager(ScriptProgressQuerySet)

    def __unicode__(self):
        if self.step:
            return "%d" % self.step.order
        else:
            return "Not Started"

    def expired(self, curtime):
        """
        Check if the wait time for this step is completed.  This applies to all
        rules except LENIENT and STRICT, which only take action when a user
        responds.  For WAIT_* rules, only the giveup time is checked,
        for RESEND_* rules, the number of resends must be reached, and then
        the giveup time exceeded.

        Returns True if it the time for this step has elapsed, False otherwise
        """
        if  self.step and self.status == ScriptProgress.PENDING and \
            (self.step.rule in [ScriptStep.WAIT_MOVEON, ScriptStep.WAIT_GIVEUP] or \
            (\
                (self.step.rule in [ScriptStep.RESEND_MOVEON, \
                                    ScriptStep.RESEND_GIVEUP, \
                                    ScriptStep.STRICT_GIVEUP, \
                                    ScriptStep.STRICT_MOVEON]) and \
                (self.num_tries >= self.step.num_tries) \
            )):
            return (self.time + datetime.timedelta(seconds=self.step.giveup_offset) <= curtime)
        return False

    def time_to_start(self, curtime):
        """
        Check if the current script progress needs to be started.  This applies when
        a ScriptProgress object has None for step (user hasn't even progressed to step
        0), and the start_offset for the first step has elapsed.

        Returns True if the above case applies, False otherwise
        """
        return (not self.step and \
                self.time + datetime.timedelta(seconds=self.script.steps.get(order=0).start_offset) <= curtime)

    def time_to_resend(self, curtime):
        """
        Check to see if the time to resend a message/poll has elapsed, based on the
        step, rules, status, num_tries, and retry_offset.

        Returns True if the step has the appropriate rule, and the proper amount of time
        has passed, False otherwise.
        """
        return (self.step and self.step.rule in [ScriptStep.RESEND_MOVEON, ScriptStep.RESEND_GIVEUP, ScriptStep.STRICT_GIVEUP, ScriptStep.STRICT_MOVEON] and \
            self.num_tries < self.step.num_tries and self.time + datetime.timedelta(seconds=self.step.retry_offset) <= curtime)

    def last_step(self):
        """
        Returns true if the current step is the last step, False otherwise.
        """
        return (self.step and \
                self.script.steps.order_by('-order')[0].order == self.step.order)

    def time_to_transition(self, curtime):
        """
        For steps that are complete, check the start time of the
        next step (or check if the current step is the last one).

        If the start_offset of the next step has elapsed, returns
        True, False otherwise.
        """
        next_step = self.get_next_step()
        return (self.step and \
                self.status == 'C' and \
                (self.last_step() or \
                self.time + datetime.timedelta(seconds=next_step.start_offset) <= curtime))

    def giveup(self):
        """
        Remove this ScriptProgress from the table, update ScriptSession, and
        fire the appropriate signal.
        """
        session = ScriptSession.objects.filter(script=self.script, connection=self.connection, end_time=None).latest('start_time')
        session.end_time = datetime.datetime.now()
        session.save()
        script_progress_was_completed.send(sender=self, connection=self.connection)
        self.delete()


    def get_next_step(self):
        steps = self.script.steps.filter(order__gt=self.step.order) if self.step else self.script.steps.all()
        if steps.count():
            return steps.order_by('order')[0]
        else:
            return None


    def moveon(self):
        """
        Move the step to the next in order (if one exists, otherwise end the script),
        sending the appropriate signals.
        """
        next_step = self.get_next_step()
        if next_step:
            script_progress_pre_change.send(sender=self, connection=self.connection, step=self.step)
            self.step = next_step
            self.status = 'P'
            self.save()
            script_progress.send(sender=self, connection=self.connection, step=self.step)
            return True
        else:
            self.giveup()
            return False

    def start(self):
        """
        start the ScriptProgress, by advancing to the zeroeth step.
        """
        ScriptSession.objects.create(script=self.script, connection=self.connection)
        self.moveon()

    def outgoing_message(self):
        """
        Return the appropriate outgoing message for this step, either the poll question
        or the message.
        """
        if self.step.poll:
            return self.step.poll.question
        elif self.step.email:
            return self.step.email
        else:
            return self.step.message

    def accepts_incoming(self, curtime):
        """
        Check to see if the current progress within the ScriptProgress is waiting
        for an incoming message: the script should be started, the current step
        should have a poll, the status should be pending and the step should not
        be past its expiry time.  Returns True if this is the case, False otherwise.
        """
        return (self.step and self.step.poll and self.status == ScriptProgress.PENDING and not self.expired(curtime))

    def log(self, response):
        """
        Log the response in the current ScriptSession for this connection.
        """
        session = ScriptSession.objects.filter(connection=self.connection, script=self.script, end_time=None).latest('start_time')
        session.responses.create(response=response)

    def set_time(self, newtime):
        """
        The time attribute is normally auto_now, for convenience (it's supposed to store
        the last time that something happened in the script).  However, for scheduling
        purposes, it's sometimes convenient to change it to something else manually.
        """
        cursor = connection.cursor()
        cursor.execute("update script_scriptprogress set time = '%s' where id = %d" %
                       (newtime.strftime('%Y-%m-%d %H:%M:%S.%f'), self.pk))


class ScriptSession(models.Model):
    """
    This model provides a full audit trail of all the responses during a particular
    progression through a script.
    """
    connection = models.ForeignKey(Connection)
    script = models.ForeignKey(Script)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True)


class ScriptResponse(models.Model):
    session = models.ForeignKey(ScriptSession, related_name='responses')
    response = models.ForeignKey(Response)


class Email(models.Model):
    subject = models.TextField()
    sender = models.EmailField(default='no-reply@uganda.rapidsms.org')
    message = models.TextField()
    recipients = models.ManyToManyField(User, related_name='emails', null=True)

    def send(self, context={}):
        recipients = list(self.recipients.values_list('email', flat=True).distinct())
        subject_template = Template(self.subject)
        message_template = Template(self.message)
        ctxt = Context(context)
        subject = subject_template.render(ctxt)
        message = message_template.render(ctxt)
        if message.strip():
            send_mail(subject, message, self.sender, recipients, fail_silently=False)

