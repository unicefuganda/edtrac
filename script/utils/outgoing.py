#!/usr/bin/python
# -*- coding: utf-8 -*-
import datetime
from script.models import ScriptStep, ScriptProgress, Script, ScriptSession
from rapidsms.models import Connection

def check_progress(connection):
    """
    This function should check if a given connection
    (of type rapidsms.models.Connection) needs to be prompted
    with any messages, based on the progress of the particular
    Connection, the rules of the particular step in the script,
    and the current time.  NOTE: This function doesn't need to
    check if the particular connection belongs to a script: this
    function is called from the check_script_progress management
    command, which will already have performed that check.  This
    utility function should only be updating the ScriptProgress model
    accordingly.

    Returns: any immediate message (as a string) that needs to be
    queued (based on the rules of the script), on None if none are
    needed.
    """
    try:
        progress = ScriptProgress.objects.filter(connection=connection, time__lte=datetime.datetime.now()).latest('time')
    except ScriptProgress.DoesNotExist:
        return None

    d_now = datetime.datetime.now()
    if progress.time_to_start(d_now):
        progress.start()
        return progress.outgoing_message()
    elif progress.expired(d_now):
        if progress.step.rule in [ScriptStep.WAIT_GIVEUP, ScriptStep.RESEND_GIVEUP, ScriptStep.STRICT_GIVEUP]:
            progress.giveup()
        else:
            progress.status = ScriptProgress.COMPLETE
            progress.save()

    elif progress.time_to_resend(d_now):
        progress.num_tries = (progress.num_tries or 0) + 1
        progress.save()
        return progress.outgoing_message()

    # This happens unconditionally, to shortcircuit the case
    # where an expired step, set to COMPLETE above,
    # can immidately transition to the next step
    d_now = datetime.datetime.now()
    if progress.time_to_transition(d_now) and progress.moveon():
        return progress.outgoing_message()

    return None

