# This Python file uses the following encoding: utf-8
import os, sys
import datetime
from django.db.models import Manager
from django.db.models.query import QuerySet
from .models import *
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

    def need_to_resend(self,script,step):
        """
        Filter the ScriptProgress objects whose  time to resend a message/poll has elapsed, based on the
        step, rules, status, num_tries, and retry_offset.

        Parameters:
        script: The script the progress object belongs to
        step: The script step  the progress is at
        """
        curtime = datetime.datetime.now()
        try:
            return self.filter(step=step, script=script,
                               step__rule__in=[step.RESEND_MOVEON, step.RESEND_GIVEUP, step.STRICT_GIVEUP,
                                               step.STRICT_MOVEON], num_tries__lt=step.num_tries,
                               time__lte=(curtime - datetime.timedelta(seconds=step.retry_offset)))
        except TypeError:
            return self.none()

    def need_to_transition(self, script,step):
        """
        Filters ScriptProgress whose script  steps that are ready to move to the next step and the start_offset
         of the next step has elapsed

          Parameters:
          script: The script the progress object belongs to
        """
        curtime = datetime.datetime.now()
        steps = script.steps.filter(order__gt=step.order)
        if steps.count():
            next_step = steps.order_by('order')[0]

            if next_step:
                return self.filter(step=step,script=script, status='C',
                                   time__lte=(curtime - datetime.timedelta(seconds=next_step.start_offset)))
        return self.none()


    def expired(self, script, step):
        curtime = datetime.datetime.now()
        give_up_rules = [step.RESEND_MOVEON, step.RESEND_GIVEUP, step.STRICT_GIVEUP,
                         step.STRICT_MOVEON, step.WAIT_MOVEON, step.WAIT_GIVEUP]
        try:
            return self.filter(step=step,script=script).filter(Q(step__rule__in=give_up_rules),
                                                                                    Q(num_tries__gte=step.num_tries), Q(
                    time__lte=(curtime - datetime.timedelta(seconds=step.start_offset))))

        except ValueError:
            return self.none()


    def giveup(self, script,step):
        """
        Removes ScriptProgress objects from the table, update ScriptSession, and
        fires the appropriate signal.
        """
        expired=self.all().expired(script,step)
        print expired
        spses=expired.filter(step__rule__in = [step.WAIT_GIVEUP, step.RESEND_GIVEUP, step.STRICT_GIVEUP])
        for sp in spses:
            session = ScriptSession.objects.filter(script=script, connection=sp.connection, end_time=None).latest('start_time')
            session.end_time = datetime.datetime.now()
            print sp.connection
            session.save()
            script_progress_was_completed.send(sender=sp, connection=sp.connection)
        return spses.delete()


    def moveon(self, script,step):
        """
        Move the step to the next in order (if one exists, otherwise end the script),
        sending the appropriate signals.
        """
        steps = script.steps.filter(order__gt=step.order)
        script_progres_objects = self.all().need_to_transition(script,step)
        if steps.count():
            next_step = steps.order_by('order')[0]
        else:
            next_step=None
        if next_step:

            for sp in script_progres_objects:
                script_progress_pre_change.send(sender=sp, connection=sp.connection, step=step)
            self.all().update(step=next_step)
            toret = self.update(status='P')
            for sp in script_progres_objects:
                script_progress.send(sender=sp, connection=sp.connection, step=next_step)
            return toret
        else:
            return self.giveup(script,step)


class ProgressManager(Manager):
    def __init__(self, qs_class=QuerySet):
        super(ProgressManager,self).__init__()
        self.queryset_class = qs_class
    def get_query_set(self):
        return ScriptProgressQuerySet(self.model, using=self._db)
    
    def __getattr__(self, attr, *args):
        try:
            return getattr(self.__class__, attr, *args)
        except AttributeError:
            return getattr(self.get_query_set(), attr, *args)
