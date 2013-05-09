#!/usr/bin/python
# -*- coding: utf-8 -*-
import datetime
from django.db.models import F
from script.models import ScriptStep, ScriptProgress, Script, ScriptSession
from rapidsms.models import Connection
from poll.models import gettext_db
import logging
module_name = __name__
logger = logging.getLogger(module_name)
def check_progress(script):
    """
    This function should check if a given script has script progress
    objects that need to be prompted
    with any messages, based on the progress of the particular
    script progress objects, the rules of the particular step in the script,
    and the current time.  This utility function should only be updating the ScriptProgress 
    objects accordingly.
    """
    for step in script.steps.order_by("-order"):
        # expire those steps that need it
        expired_progress_objects = ScriptProgress.objects.expired(script, step)
        if expired_progress_objects.exists():
            expired_progress_objects.expire(script, step)

        to_resend = ScriptProgress.objects.need_to_resend(script, step)
        if to_resend.exists():
            logger.debug("[%s] Resending messages for pending scripts with ids: %s.\n" % (module_name,str(to_resend)))
            to_resend_list = list(to_resend.values_list('pk', flat=True))
            to_resend.filter(num_tries=None).update(num_tries=0)
            to_resend.update(num_tries=F('num_tries') + 1, time=datetime.datetime.now())
            ScriptProgress.objects.filter(pk__in=to_resend_list).mass_text()

        # This happens unconditionally, to shortcircuit the case
        # where an expired step, set to COMPLETE above,
        # can immidately transition to the next step
        to_transition = ScriptProgress.objects.need_to_transition(script, step)
        to_trans_list = list(to_transition.values_list('pk', flat=True))
        if to_transition.exists():
            logger.debug("[%s] Need to transition scripts with ids %s.\n" % (module_name,str(to_transition)))
            to_transition.moveon(script, step)
            ScriptProgress.objects.filter(pk__in=to_trans_list).filter(num_tries=None).update(num_tries=0)
            ScriptProgress.objects.filter(pk__in=to_trans_list).update(num_tries=F('num_tries') + 1, time=datetime.datetime.now())
            ScriptProgress.objects.filter(pk__in=to_trans_list).mass_text()

    to_start = ScriptProgress.objects.need_to_start(script)
    to_start_list = list(to_start.values_list('pk', flat=True))
    if to_start.exists():
        logger.debug("[%s] Starting  scripts with ids : %s.\n" % (module_name,str(to_start)))
        for sp in to_start:
            ScriptSession.objects.create(script=sp.script, connection=sp.connection)

        to_start.moveon(script, None)
        ScriptProgress.objects.filter(pk__in=to_start_list).filter(num_tries=None).update(num_tries=0)
        ScriptProgress.objects.filter(pk__in=to_start_list).update(num_tries=F('num_tries') + 1, time=datetime.datetime.now())


        ScriptProgress.objects.filter(pk__in=to_start_list).mass_text()
