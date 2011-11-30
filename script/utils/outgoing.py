#!/usr/bin/python
# -*- coding: utf-8 -*-
import datetime
from django.db.models import F
from script.models import ScriptStep, ScriptProgress, Script, ScriptSession
from rapidsms.models import Connection
from poll.models import gettext_db

def check_progress(script):
    """
    This function should check if a given script has script progress
    objects that need to be prompted
    with any messages, based on the progress of the particular
    script progress objects, the rules of the particular step in the script,
    and the current time.  This utility function should only be updating the ScriptProgress 
    objects accordingly.
    """

    to_start = ScriptProgress.objects.need_to_start(script).moveon(script, None)
    for sp in to_start:
        ScriptSession.objects.create(script=sp.script, connection=sp.connection)
    # FIXME: mass text for to_start

    for step in script.steps.all():
        # expire those steps that need it
        ScriptProgress.objects.expired(script, step).expire(script, step).expire(script, step)

        to_resend = ScriptProgress.objects.need_to_resend(script, step)
        to_resend.filter(num_tries=None).update(num_tries=0)
        to_resend.update(num_tries=F('num_tries') + 1)
        # FIXME: mass text for resend
#        if progress.language:
#            return gettext_db(progress.outgoing_message(), progress.language)

        # This happens unconditionally, to shortcircuit the case
        # where an expired step, set to COMPLETE above,
        # can immidately transition to the next step
        to_transition = ScriptProgress.objects.need_to_transition(script, step)
        to_transition.moveon(script, step)
        # FIXME: mass text for transition

#        if progress.language:
#            return gettext_db(progress.outgoing_message(), progress.language)
