#!/usr/bin/python
# -*- coding: utf-8 -*-
import datetime
from script.models import ScriptStep, ScriptProgress, Script
from rapidsms.models import Connection


def prog_msg(progress):
    if progress.step:
        if progress.step.poll:
            return progress.step.poll.question
        else:
            return progress.step.message
    else:

        return None


def can_moveon(progress):
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

    # means its the first step in the script . get the initial step and check if its due to be sent.

    if not progress.step:
        if current_time \
            >= datetime.timedelta(seconds=progress.get_initial_step().start_offset) \
            + progress.time:
            progress.step = progress.get_initial_step()
            progress.status = 'P'
            progress.save()
            return prog_msg(progress)
        else:
            return None
    else:

        # #check for completed step

        if progress.step == 'C':

            # is this the last step?

            if progress.step == progress.get_last_step():
                return None
            elif current_time \
                >= datetime.timedelta(seconds=progress.get_next_step().start_offset) \
                + progress.time:

            # get the next step and check its start_offset offset

                progress.step = progress.get_next_step()
                progress.status = 'P'
                progress.save()
                return prog_msg(progress)
            else:
                return None
        else:

        # current progress is in progress

            # check giveup offset

            giveup_offset = progress.step.giveup_offset
            if giveup_offset:
                if current_time >= progress.time \
                    + datetime.timedelta(seconds=giveup_offset):
                    if progress.step.rule == ScriptStep.WAIT_MOVEON:
                        next_step = progress.get_next_step()
                        if next_step:
                            if can_moveon(progress):
                                progress.step = next_step
                                progress.save()
                                return prog_msg(progress)
                            else:
                                return None
                        else:
                            if progress.step \
                                == progress.get_last_step():
                                progress.status = 'C'
                                progress.save()
                            return None
                    if progress.step.rule == ScriptStep.WAIT_GIVEUP:
                        progress.delete()
                        return None

            # check number of tries

            if progress.num_tries and progress.num_tries \
                == progress.step.num_tries:
                if progress.step.rule == ScriptStep.RESEND_MOVEON \
                    and can_moveon(progress):
                    step = progress.get_next_step()
                    if step:
                        progress.step = step
                        progress.save()
                        return prog_msg(progress)
                    else:
                        if progress.step == progress.get_last_step():
                            progress.status = 'C'
                            progress.save()
                        return None
                elif progress.step.rule == ScriptStep.RESEND_GIVEUP:
                    progress.delete()
                    return None
                else:
                    return None
            elif progress.num_tries < progress.step.num_tries:
                if progress.num_tries:
                    progress.num_tries += 1
                    progress.save()
                else:
                    progress.num_tries = 1
                    progress.save()
                return prog_msg(progress)

            if can_moveon(progress):
                progress.step = progress.get_next_step()
                progress.save()
                return prog_msg(progress)
            elif progress.step == progress.get_last_step():

                progress.status = 'C'
                progress.save()
                return None

    return prog_msg(progress)


