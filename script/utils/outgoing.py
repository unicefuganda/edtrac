import datetime
from script.models import ScriptStep,ScriptProgress,Script
from rapidsms.models import  Connection

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
    progress=ScriptProgress.objects.get(connection=connection)
    number_of_script_steps=progress.script.steps.order_by('-order')[0].order
    current_time=datetime.datetime.now()
    if not progress.step:
        progress.step=progress.get_initial_step()
        progress.status='P'
        progress.save()
    elif progress.step.order == number_of_script_steps and progress.step=='C':

        return None
    elif  current_time >= progress.time+datetime.timedelta(seconds=progress.step.giveup_offset):
        progress.status='C'
        progress.save()
        return None
    elif progress.num_tries==progress.step.num_tries :
        if progress.step.rule in ['r','g']:
            progress.status='C'
            progress.save()
            return None
        elif progress.step.rule in ['R','w']:
            progress.step=progress.get_next_step()
            progress.status='P'
            progress.save()

    elif progress.step==progress.get_initial_step() and progress.status=='C':
        progress.step=progress.get_next_step()
        progress.status='P'
        progress.save()


    elif current_time >= progress.time+datetime.timedelta(seconds=progress.step.start_offset):
        progress.step=progress.get_next_step()
        progress.step.save()
        progress.save()

    else:
        return None
    if progress.step.poll:

        return progress.step.poll.question
    else:
        return progress.step.message
