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
    current_step = progress.step
    next_step = progress.get_next_step()
    if progress.step.poll:
        response = progress.step.poll.process_response(message)
    else:
        response = None
    current_poll_question = current_step.poll.question
    current_time = datetime.datetime.now()

#    if current step status is PENDING ********************************
    if progress.status == 'P':

#        EVALUATE THE LENIENT RULE for PENDING state************************************

        if progress.step.rule == 'l':
#            its a poll but answered incorrectly!
            if response and response[0].has_errors:
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
#                Old step complete
                    progress.status = 'C'
                    progress.save()

#                   New step start
                    if progress.proceed():
                        progress.step = next_step
                        progress.status = 'P'
                        progress.save()
                        if next_step.poll:
                            return next_step.poll.question
#                        next step is not a poll but a message
                        else:
                            return next_step.message
                    else:
#                        Not yet time to start new step
                        return None
                else:
#                    the response from poll processing is not none and there are no errors
                    progress.status = 'C'
                    progress.save()
                    return response[1]
                
#            its not a poll response but a simple message
            else:
                progress.status = 'C'
                progress.save()

#                Proceed to next step?
                if progress.proceed():
                    progress.step = next_step
                    progress.status = 'P'
                    progress.save()
                    if next_step.poll:
                        return next_step.poll.question
                    else:
                        return next_step.message
                else:
                    return None
                
#        EVALUATE THE RETRY MOVE-ON and RETRY GIVE-UP Rules together for PENDING state ***************************

        elif progress.step.rule == 'R' or progress.step.rule == 'r':
            if response and response[0].has_errors:
                if progress.keep_retrying():
                    if progress.retry_now():
                        if progress.current_step.rule == 'r':
    #                        if rule is resend-giveup, delete connection!
                            progress.delete()
                        else:
                            progress.num_tries += 1
                            progress.status = 'C'
                            progress.save()
                            
                        return current_poll_question
                    else:
                        return None
#                Don't keep retrying
                else:
                    progress.status = 'C'
                    progress.save()
                    
#                    Proceed to next step?
                    if progress.proceed():
                        progress.step = next_step
                        progress.status = 'P'
                        progress.save()
                        if next_step.poll:
                            return next_step.poll.question
                        else:
                            return next_step.message
                    else:
                        return None

#            its a correct poll response
            elif response and not response[0].has_errors:
                if response[1] is None:
                    progress.status = 'C'
                    progress.save()

#                    Try to move to the next step
                    if progress.proceed():
                        progress.step = next_step
                        progress.status = 'P'
                        progress.save()
                        if next_step.poll:
                            return next_step.poll.question
#                        next step is not a poll but a message
                        else:
                            return next_step.message
                    else:
#                        Not yet time to start new step
                        return None

                    return None
#                There is a valid response from poll processing
                else:
                    progress.status = 'C'
                    progress.save()
                    return response[1]

#            its a simple message
            else:
                progress.status = 'C'
                progress.save()

#                Proceed to next step?
                if progress.proceed():
                    progress.step = next_step
                    progress.status = 'P'
                    progress.save()
                    if next_step.poll:
                        return next_step.poll.question
                    else:
                        return next_step.message
                else:
                    return None
        else:

#           EVALUATE THE WAIT MOVE-ON and WAIT GIVE-UP Rules together for PENDING state ******************************

#            TODO: evaluate Wait Move-on and Wait Give up rules
            progress.status = 'C'
            progress.save()
    else:

#    Current step status is COMPLETE 'C' ********************************
#        TODO: evaluate all rules

        response = poll.process_response(message)
        return response[1]