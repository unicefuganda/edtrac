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

#    if check_progress has fired up the initial step
    if current_step:
#        if the step is a poll
        if current_step.poll:
        #    if current step status is PENDING ********************************
            if progress.status == ScriptProgress.PENDING:
        #        EVALUATE THE STRICT RULE for PENDING state************************************

#                is the rule strict?
                if progress.step.rule == ScriptStep.STRICT:
                    response = progress.step.poll.process_response(message)
        #            its a poll but answered incorrectly!
                    if response[0].has_errors:
        #                record response to this step
                        response_trail(progress, response)
                        return response[1]

        #            its a poll response and answered correctly
                    else:
        #                if we have a valid message from process_response()
                        progress.status = ScriptProgress.COMPLETE
                        progress.save()
                        response_trail(progress, response)

        #        EVALUATE THE LENIENT RULE for PENDING state************************************
                elif progress.step.rule == ScriptStep.LENIENT:
                    response = progress.step.poll.process_response(message)
                    progress.status = ScriptProgress.COMPLETE
                    progress.save()
                    response_trail(progress, response)
                    return response[1]

        #        EVALUATE THE RETRY MOVE-ON and RETRY GIVE-UP Rules together for PENDING state ***************************
                elif progress.step.rule == ScriptStep.RESEND_MOVEON or progress.step.rule == ScriptStep.RESEND_GIVEUP:
                    if progress.give_up_now():
                        return None
                    else:
                        response = progress.step.poll.process_response(message)
                        if response[0].has_errors:
                            response_trail(progress, response)
                            return response[1]
                        else:
                            progress.status = ScriptProgress.COMPLETE
                            progress.save()
                            response_trail(progress, response)
                            return response[1]

        #           EVALUATE THE WAIT MOVE-ON and WAIT GIVE-UP Rules together for PENDING state ******************************
                else:
        #            is it time to give up?
                    if progress.give_up_now():
                        return None
                        
        #            Not yet time to give up, Move on!
                    else:
        #                Simply Complete this step
                        response = progress.step.poll.process_response(message)
                        progress.status = ScriptProgress.COMPLETE
                        progress.save()
                        response_trail(progress, response)
                        return None

        #         Current step status is COMPLETE 'C' ********************************
            else:
                return None
#            Not a poll but just static message
        else:
            return None
#        Still waiting for check_progress()
    else:
        return None

    
def response_trail(progress, response):
#    is this a poll
    connection = progress.connection
    script = progress.step.script
    resp = response[0]
    session = ScriptSession.objects.get(connection=connection, script=script)
    session.responses.create(response = resp)

    
            