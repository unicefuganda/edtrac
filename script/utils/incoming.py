import datetime
from script.models import ScriptProgress, ScriptStep
from poll.models import Poll

def incoming_progress(message):
    """
    This function should check if an incoming message
    (of type rapidsms.messages.incoming.IncomingMessage)
    moves a particular script forward, based on the progress
    of the particular Connection and the rules of the particular
    step.  NOTE: This function doesn't need to check if the particular
    connection belongs to a script: this function is called from
    app.py, which will already have performed that check.  This utility
    function should only be updating the ScriptProgress model accordingly.

    This function SHOULD, however, do all processing of the message (i.e.,
    updating the ScriptProgress table, calling Poll.process_response, etc.),
    and also fire any signals on script progression or completion.

    Returns: any immediate response (as a string) that is necessary (based on
    the rules of the script), or None if none are needed.
    """
    progress = ScriptProgress.objects.get(connection=message.connection)
    num_script_steps = ScriptStep.objects.get(script=progress.script).count()
    script_last_step = ScriptStep.objects.get(script=progress.script).order_by('-order')[0]
    next_step = ScriptStep.objects.get(script=progress.script,order=progress.step.order+1)
    current_time=datetime.datetime.now()
    if progress.status == 'P':
        response = Poll.process_response(message)
        if response[0].has_errors:
            if progress.step.rule == 'l':
                if script_last_step == num_script_steps:
                    progress.status = 'C'
                    return None
                else:
                    progress.step = next_step
                    progress.num_tries = progress.num_tries + 1
                    progress.save()
                    return None
            elif progress.step.rule == 'R' or progress.step.rule == 'r':
                step = ScriptStep.objects.get(script=progress.script)
                current_poll_question = step.poll.question
                if progress.num_tries < step.retry_offset:
                    progress.num_tries = progress.num_tries + 1
                    if progress.step.rule == 'r':
                        progress.status = 'C'
                    return current_poll_question
                else:
                    progress.step = next_step
                    return None
            else:
                pass
        else:
            return response[1]
    else:
        response = Poll.process_response(message)
        return response[1]