import datetime

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
    pass