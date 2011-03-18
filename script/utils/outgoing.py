#!/usr/bin/python
# -*- coding: utf-8 -*-
import datetime
from script.models import ScriptStep, ScriptProgress, Script
from rapidsms.models import Connection


def prog_msg(progress):
    """
    return either poll or message
    """

    if progress.step:
        if progress.step.poll:
            return progress.step.poll.question
        else:
            return progress.step.message
    else:

        return None


def can_moveon(progress):
    """ tests if the scriptprogress can move to the next step"""

    if progress.get_next_step() and datetime.datetime.now() \
        >= progress.time \
        + datetime.timedelta(seconds=progress.get_next_step().start_offset):
        return True
    elif progress.status == 'P' and progress.step.rule \
        == ScriptStep.STRICT:
        return False
    else:
        return False


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

    progress = ScriptProgress.objects.get(connection=connection)
    current_time = datetime.datetime.now()


    # having no step means the ScriptProgress is unstarted . get the initial step and check if its due to be sent.
    #put the progress script in the initial sate

    if not progress.step:
        if current_time \
            >= datetime.timedelta(seconds=progress.get_initial_step().start_offset) \
            + progress.time:
            progress.move_to_nextstep()
            return prog_msg(progress)
        else:
            return None
    else:

        # #check for completed step

        if progress.status == 'C':

            # is this the last step?

            if progress.step == progress.get_last_step():
                return None
            elif current_time \
                >= datetime.timedelta(seconds=progress.get_next_step().start_offset) \
                + progress.time:

            # get the next step and check its start_offset offset

                progress.move_to_nextstep()
                return prog_msg(progress)
            else:
                return None
        else:

        # current progress is in progress
            if progress.step.giveup_offset:
                if current_time >= progress.time \
                    + datetime.timedelta(seconds=progress.step.giveup_offset):
                    if progress.step.rule == ScriptStep.WAIT_MOVEON:
                        next_step = progress.get_next_step()
                        if next_step:
                            if can_moveon(progress):
                                progress.move_to_nextstep()
                                return prog_msg(progress)
                            else:
                                return None
                        else:
                            return prog_msg(progress)
                    if progress.step.rule == ScriptStep.WAIT_GIVEUP:
                        progress.delete()
                        return None

            # check number of tries
            if progress.step.num_tries:
                if progress.num_tries == progress.step.num_tries:
                    if progress.step.rule == ScriptStep.RESEND_MOVEON \
                        and can_moveon(progress):
                        step = progress.get_next_step()
                        if step:
                            progress.move_to_nextstep()
                            return prog_msg(progress)
                    if progress.step.rule == ScriptStep.RESEND_GIVEUP:
                        progress.delete()
                        return None

                    if can_moveon(progress):
                        progress.move_to_nextstep()
                        return prog_msg(progress)
                    else:
                        return None
                if progress.num_tries < progress.step.num_tries:
                     if current_time \
            > datetime.timedelta(seconds=progress.step.retry_offset) \
            + progress.time:
                        if progress.num_tries:
                            progress.num_tries += 1
                            progress.save()
                        else:
                            progress.num_tries = 1
                            progress.save()
                        return prog_msg(progress)
                     else:
                         return None


            if can_moveon(progress):
                progress.move_to_nextstep()
                return prog_msg(progress)
            else:
                return None

    return prog_msg(progress)


