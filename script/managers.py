# This Python file uses the following encoding: utf-8
import os, sys
import datetime
from django.db.models import Manager
from django.db.models.query import QuerySet
from .models import *
from rapidsms_httprouter.models import Message
from poll.models import gettext_db
from django.db.models import Q

class ScriptProgressQuerySet(QuerySet):
    def need_to_start(self, script):
        """
        Filter to script progress objects that need to be started.  This applies when
        a ScriptProgress object has None for step (user hasn't even progressed to step
        0), and the start_offset for the first step has elapsed.

        Returns all ScriptProgress objects for which the above rules apply, 
        for a given script.
        
        Parameters:
        script : The particular script that we're currently concerned with
        
        Example:
        script = Script.objects.all()[0] # get the first script in the db
        # returns all ScriptProgress objects
        # that need to complete start this script
        ScriptProgress.objects.all().need_to_start(script)
        """
        curtime = datetime.datetime.now()
        start_offset = script.steps.get(order=0).start_offset
        return self.filter(step=None, time__lte=(curtime - datetime.timedelta(seconds=start_offset)))

    def need_to_resend(self, script, step):
        """
        Filter the ScriptProgress objects whose  time to resend a message/poll has elapsed, based on the
        step, rules, status, num_tries, and retry_offset.

        Parameters:
        script: The script the progress object belongs to
        step: The script step  the progress is at
        """
        if step.retry_offset is None:
            return self.none()

        curtime = datetime.datetime.now()
        toret = self.filter(step=step, script=script,
                           step__rule__in=[step.RESEND_MOVEON, step.RESEND_GIVEUP, step.STRICT_GIVEUP,
                                           step.STRICT_MOVEON],
                           time__lte=(curtime - datetime.timedelta(seconds=step.retry_offset)))
        return toret.filter(Q(num_tries__lt=step.num_tries) | Q(num_tries=None))

    def need_to_transition(self, script, step):
        """
        Filters ScriptProgress whose script  steps that are ready to move to the next step and the start_offset
         of the next step has elapsed

          Parameters:
          script: The script the progress object belongs to
        """
        if not step:
            return self.none()
        curtime = datetime.datetime.now()

        next_steps = script.steps.filter(order__gt=step.order).order_by('order')
        next_step = None
        if next_steps.exists():
            next_step = next_steps[0]

        if next_step:
            return self.filter(step=step, script=script, status='C',
                               time__lte=(curtime - datetime.timedelta(seconds=next_step.start_offset)))
        else:
            # if there isn't a next step, we're at the end of the script,
            # and all ScriptProgress objects in "C"omplete status
            # need to be transitioned to giveup()
            return self.filter(step=step, script=script, status="C")



    def expired(self, script, step):
        curtime = datetime.datetime.now()
        if step.giveup_offset is None:
            return self.none()

        toret = self.filter(step=step, script=script, status=self.model.PENDING, \
                            time__lte=(curtime - datetime.timedelta(seconds=step.giveup_offset)))
        if step.rule in [step.WAIT_MOVEON, step.WAIT_GIVEUP]:
            return toret
        elif step.rule in [step.RESEND_MOVEON, \
                                    step.RESEND_GIVEUP, \
                                    step.STRICT_GIVEUP, \
                                    step.STRICT_MOVEON]:
            return toret.filter(num_tries__gte=step.num_tries)
        else:
            return self.none()

    def expire(self, script, step):
        give_up_rules = [step.WAIT_GIVEUP, step.RESEND_GIVEUP, step.STRICT_GIVEUP]
        self.filter(step__rule__in=give_up_rules).giveup(script, step)
        self.exclude(step__rule__in=give_up_rules).update(status=self.model.COMPLETE, time=datetime.datetime.now())

    def giveup(self, script, step):
        """
        Removes ScriptProgress objects from the table, update ScriptSession, and
        fires the appropriate signal.
        """
        from script.models import ScriptSession
        spses = self
        for sp in spses:
            session = ScriptSession.objects.filter(script=script, connection=sp.connection, end_time=None).latest(
                'start_time')
            session.end_time = datetime.datetime.now()
            session.save()
            script_progress_was_completed.send(sender=sp, connection=sp.connection)
        return spses.delete()

    def moveon(self, script, step):
        """
        Move the step to the next in order (if one exists, otherwise end the script),
        sending the appropriate signals.
        """
        if step:
            steps = script.steps.filter(order__gt=step.order)

        else:
            steps = script.steps.all()

        script_progress_list = list(self.values_list('pk', flat=True))

        if steps.count():
            next_step = steps.order_by('order')[0]
        else:
            next_step = None
        if next_step:
            for sp in self:
                script_progress_pre_change.send(sender=sp, connection=sp.connection, step=step)
            self.update(step=next_step, status=self.model.PENDING, time=datetime.datetime.now())
            for sp in self.model._default_manager.filter(pk__in=script_progress_list):
                script_progress.send(sender=sp, connection=sp.connection, step=next_step)
            return True
        else:
            return self.giveup(script, step)

    def mass_text(self):
        #get one scriptprogress since they are all supposed to be on the same step
        if self.exists():
            prog = self[0]
        else:
            return False
        if prog.step.poll:
            text = prog.step.poll.question
        elif prog.step.email:
            text = prog.step.email
        else:
            text = prog.step.message

        for language in dict(settings.LANGUAGES).keys():
            if language == "en":
                """default to English for contacts with no language preference"""
                localized_progs = self.filter(Q(language__in=["en", '']) | Q(language=None))
            else:
                localized_progs = self.filter(language=language)

            if localized_progs.exists():
                localized_conns = localized_progs.values_list('connection', flat=True)
                messages = Message.mass_text(gettext_db(field=text, language=language),
                                             Connection.objects.filter(pk__in=localized_conns).distinct(), status='L')
        return True


class ProgressManager(Manager):
    def __init__(self, qs_class=QuerySet):
        super(ProgressManager, self).__init__()
        self.queryset_class = qs_class

    def get_query_set(self):
        return ScriptProgressQuerySet(self.model, using=self._db)

    def __getattr__(self, attr, *args):
        try:
            return getattr(self.__class__, attr, *args)
        except AttributeError:
            return getattr(self.get_query_set(), attr, *args)
