# This Python file uses the following encoding: utf-8
import os, sys
import datetime
from django.db.models import Manager
from django.db.models.query import QuerySet

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

    def need_to_resend(self, curtime):
        return self

    def need_to_transition(self, curtime):
        return self

    def giveup(self):
        return self

    def moveon(self):
        return self

    def outgoing_message(self):
        return self

    def accepts_incoming(self, curtime):
        return self


class ProgressManager(Manager):
    def get_query_set(self):
        return ScriptProgressQuerySet(self.model, using=self._db)
