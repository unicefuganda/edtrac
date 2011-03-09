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
    progress=ScriptProgress.objects.get(connection=connection)
    number_of_script_steps=progress.script.steps.order_by('-order')[0].order
    current_time=datetime.datetime.now()
    if not progress.step:
        progress.status='P'
        progress.save()
        progress.step=progress.script.steps.get(order=0)
        progress.save()
        return progress.step.message


    elif progress.step.order==0 and progress.status:
        progress.step=ScriptStep.objects.get(script=progress.script,order=1)
        progress.step.save()
        progress.status='P'
        progress.save()
        if progress.step.poll:
            return progress.step.poll.question

    elif current_time >= progress.time:

        if progress.step.order == number_of_script_steps:
            progress.status='C'
            progress.save()
            return None
        progress.step=ScriptStep.objects.get(script=progress.script,order=progress.step.order+1)
        progress.step.save()
        progress.save()
        if progress.step.poll:
            return progress.step.poll.question

    return progress.step.poll.question