import datetime
from script.models import ScriptProgress, ScriptStep, ScriptSession

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
    progress = None
    try:
        progress = ScriptProgress.objects.get(connection=message.connection)
    except ScriptProgress.DoesNotExist:
        # potential race condition where ScriptProgress is deleted by check_progress
        pass
    curtime = datetime.datetime.now()
    if  progress and progress.accepts_incoming(curtime):
        response = progress.step.poll.process_response(message)
        progress.log(response[0])
        if not (response[0].has_errors and\
                progress.step.rule in [ScriptStep.STRICT,\
                                       ScriptStep.STRICT_MOVEON,\
                                       ScriptStep.STRICT_GIVEUP]):
            progress.status = ScriptProgress.COMPLETE
            progress.save()
        elif response[0].has_errors and progress.step.rule in [ScriptStep.STRICT_MOVEON,\
                                                               ScriptStep.STRICT_GIVEUP]:
            progress.num_tries = (progress.num_tries or 0) + 1
            progress.save()
        return response[1]
    return None

