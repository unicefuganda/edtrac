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
    progress = ScriptProgress.objects.get(connection=message.connection)
    current_step = progress.step
    next_step = progress.get_next_step()
    if progress.step.poll:
        response = progress.step.poll.process_response(message)
    else:
        response = None
    current_poll_question = current_step.poll.question
#    if current step status is PENDING ********************************
    if progress.status == ScriptProgress.PENDING:
#        EVALUATE THE STRICT RULE for PENDING state************************************
        if progress.step.rule == ScriptStep.STRICT:
#            its a poll but answered incorrectly!
            if response and response[0].has_errors:
#                record response to this step
                response_trail(progress, response)
                if progress.retry_now():
                    if response[1] is None:
                        return current_poll_question
                    else:
                        return response[1]
                else:
                    return None
#            its a poll response and answered correctly
            elif response and not response[0].has_errors:
#                if we have a valid message from process_response()
                if response[1] is None:
#                    This step is complete
                    progress.status = ScriptProgress.COMPLETE
                    progress.save()
#                   Try next step
                    return try_next_step(progress, next_step, response)
                else:
#                    the response from poll processing is not none and there are no errors
                    progress.status = ScriptProgress.COMPLETE
                    progress.save()
                    response_trail(progress, response)
                    return response[1]
#            its not a poll response but a simple message
            else:
                progress.status = ScriptProgress.COMPLETE
                progress.save()
#                Proceed to next step?
                return try_next_step(progress, next_step, response)
            
#        EVALUATE THE LENIENT RULE for PENDING state************************************
        elif progress.step.rule == ScriptStep.LENIENT:
            progress.status = ScriptProgress.COMPLETE
            progress.save()
            response_trail(progress, response)
            if response:
                if not response[1] is None:
                    return response[1]
                else:
                    return None
            else:
                return None

#        EVALUATE THE RETRY MOVE-ON and RETRY GIVE-UP Rules together for PENDING state ***************************
        elif progress.step.rule == ScriptStep.RESEND_MOVEON or progress.step.rule == ScriptStep.RESEND_GIVEUP:
            if response and response[0].has_errors:
                if progress.keep_retrying():
                    if progress.retry_now():
                        if progress.current_step.rule == ScriptStep.RESEND_GIVEUP:
    #                        if rule is resend-giveup, delete connection!
                            progress.delete()
                        else:
                            progress.num_tries += 1
                            progress.status = ScriptProgress.COMPLETE
                            progress.save()
                        
#                        record the response
                        response_trail(progress, response)    
                        return current_poll_question
                    else:
                        return None
#                Don't keep retrying
                else:
                    progress.status = ScriptProgress.COMPLETE
                    progress.save()
#                    Proceed to next step?
                    return try_next_step(progress, next_step, response)
#            its a correct poll response
            elif response and not response[0].has_errors:
                if response[1] is None:
                    progress.status = ScriptProgress.COMPLETE
                    progress.save()
#                    Try to move to the next step
                    return try_next_step(progress, next_step, response)
#                There is a valid response from poll processing
                else:
                    progress.status = ScriptProgress.COMPLETE
                    progress.save()
                    response_trail(progress, response)
                    return response[1]
#            its a simple message
            else:
                progress.status = ScriptProgress.COMPLETE
                progress.save()
#                Proceed to next step?
                return try_next_step(progress, next_step, response
                )
        else:
#           EVALUATE THE WAIT MOVE-ON and WAIT GIVE-UP Rules together for PENDING state ******************************
#            is it time to give up?
            if progress.give_up_now():
                if progress.step.rule == ScriptStep.WAIT_GIVEUP:
#                    We are really not concerned with this connection any more, we are simply giving up
                    progress.delete()
                    return None
                else:
#                    Simply Complete this step
                    progress.status = ScriptProgress.COMPLETE
                    progress.save()
                    response_trail(progress, response)
                    return None
#            Not yet time to give up!
            else:
#                Simply Complete this step
                progress.status = ScriptProgress.COMPLETE
                progress.save()
                response_trail(progress, response)
                return None
    else:
#    Current step status is COMPLETE 'C' ********************************
#        Try next step
#        return try_next_step(progress, next_step)
#        Is it time to proceed to next step?
        if next_step and progress.proceed():
            progress.step = next_step
            progress.status = ScriptProgress.PENDING
            progress.save()
            if next_step.poll:
                return next_step.poll.question
#        next step is not a poll but a message
            else:
                return next_step.message
#    is this the last step for this connection
        elif is_last_step(progress) and progress.status == ScriptProgress.COMPLETE:
#        end of the road for this connection
            progress.delete()        
            return None
        else:
#        Not yet time to start new step
            return None


def try_next_step(progress, next_step, response):
#    since step is complete, update session
    response_trail(progress, response)
#    Is it time to proceed to next step?
    if next_step and progress.proceed():
        progress.step = next_step
        progress.status = ScriptProgress.PENDING
        progress.save()
        if next_step.poll:
            return next_step.poll.question
#        next step is not a poll but a message
        else:
            return next_step.message
#    is this the last step for this connection
    elif is_last_step(progress) and progress.status == ScriptProgress.COMPLETE:
#        end of the road for this connection
        progress.delete()        
        return None
    else:
#        Not yet time to start new step
        return None
    
def response_trail(progress, response):
#    is this a poll
    if progress.step.poll:
        connection = progress.connection
        script = progress.step.script
        resp = response[0]
#        is this the initial step?
        if progress.get_initial_step():
#            make sure the session for this connection doesn't exist already?
            if not ScriptSession.objects.get(connection=connection, script=script):
                session = ScriptSession.objects.create(
                                        connection= connection,
                                        script = script
                                        )
                session.save()
                session.responses.create(response = resp)
                session.save()
#            somehow session exists already
            else:
                session = ScriptSession.objects.get(connection=connection, script=script)
                session.responses.create(response = resp)
#        is this the last step?
        elif is_last_step(progress=progress):
            session = ScriptSession.objects.get(connection=connection, script=script)
            session.end_time = datetime.datetime.now()
            session.responses.create(response = resp)
            session.save()
#        not an initial step and not the last step
        else:
            session = ScriptSession.objects.get(connection=connection, script=script)
            session.responses.create(response = resp)
    

def is_last_step(progress):   
    if progress.step == progress.get_last_step():
        return True
    else:
        return False
    
            