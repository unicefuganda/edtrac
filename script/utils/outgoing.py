import datetime

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
    pass