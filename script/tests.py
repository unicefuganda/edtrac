"""
Basic tests for RapidSMS-Script
"""

from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.core.exceptions import ValidationError
from django.contrib.sites.models import Site
from rapidsms.models import Contact
from script.utils.incoming import incoming_progress
from script.utils.outgoing import check_progress
from script.models import *
from script.signals import *
from rapidsms.models import Contact, Connection, Backend
from rapidsms.messages.incoming import IncomingMessage
from rapidsms_httprouter.models import Message
from django.contrib.auth.models import User
from poll.models import Poll, Response
from django.conf import settings
from django.db import connection
import datetime

class ModelTest(TestCase): #pragma: no cover

    def setUp(self):
        """
        Create a default script for all test cases
        """
        site = Site.objects.get_or_create(pk=settings.SITE_ID, defaults={
            'domain':'example.com',
        })
        user = User.objects.create_user('admin', 'test@test.com', 'p4ssw0rd')
        connection = Connection.objects.create(identity='8675309', backend=Backend.objects.create(name='TEST'))
        script = Script.objects.create(
                slug="test_autoreg",
                name="The dummy registration script",
        )
        script.sites.add(Site.objects.get_current())
        script.steps.add(ScriptStep.objects.create(
            script=script,
            message='Welcome to Script!  This system is awesome!  We will spam you with some personal questions now',
            order=0,
            rule=ScriptStep.WAIT_MOVEON, # for static messages (no expected response), this is the default rule
            start_offset=0, # start one second after the user joins the script
            giveup_offset=3600, # wait one hour to spam them again
        ))
        poll = Poll.create_freeform('question1', 'First question: what is your favorite way to be spammed?  Be DESCRIPTIVE', '', [], user)
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=poll,
            order=1,
            rule=ScriptStep.WAIT_MOVEON, # for polls, this likely means a poll whose answer we aren't particularly concerned with
            start_offset=0, #start immediately after the giveup time has elapsed from the previous step
            giveup_offset=86400, # we'll give them a full day to respond
        ))
        poll2 = Poll.create_yesno('question2', 'Second question: Do you like CHEESE?', 'Thanks for your cheesy response!', [], user)
        poll2yes = poll2.categories.get(name='yes')
        poll2yes.response = "It's very good to know that you like cheese!"
        poll2yes.save()
        poll2unknown = poll2.categories.get(name='unknown')
        poll2unknown.response = "We didn't understand your response and it's very important to know about your cheese desires.  Please resend."
        poll2unknown.save()
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=poll2,
            order=2,
            rule=ScriptStep.STRICT, # we really want to know how the user feels about cheese
            start_offset=0, #start immediately after the giveup time has elapsed from the previous step
        ))
        script.steps.add(ScriptStep.objects.create(
            script=script,
            message='Thank you for using script!  We hope you had an awesome/cheesy time!',
            order=3,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=3600, # wait an hour, because they got the poll's response in this case
            giveup_offset=0, # complete the script immediately after this message is sent 
        ))

    def elapseTime(self, progress, seconds):
        """
        This hack mimics the progression of time, from the perspective of a linear test case,
        by actually *subtracting* from the value that's currently stored (usually datetime.datetime.now())
        """
        cursor = connection.cursor()
        newtime = progress.time - datetime.timedelta(seconds=seconds)
        cursor.execute("update script_scriptprogress set time = '%s' where id = %d" %
                       (newtime.strftime('%Y-%m-%d %H:%M:%S.%f'), progress.pk))
        try:
            session = ScriptSession.objects.get(connection=progress.connection, end_time=None)
            session.start_time = session.start_time - datetime.timedelta(seconds=seconds)
            session.save()
        except ScriptSession.DoesNotExist:
            pass

    def fakeIncoming(self, message, connection=None):
        if connection is None:
            connection = Connection.objects.all()[0]
        # if so, process it
        incomingmessage = IncomingMessage(connection, message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=connection, text=message)
        return incomingmessage

    def testCheckProgress(self):
        connection = Connection.objects.all()[0]
        script = Script.objects.all()[0]
        prog = ScriptProgress.objects.create(connection=connection, script=script)
        response = check_progress(connection)

        self.assertEquals(response, 'Welcome to Script!  This system is awesome!  We will spam you with some personal questions now')
        self.assertEquals(ScriptSession.objects.count(), 1)
        self.assertEquals(ScriptSession.objects.all()[0].responses.count(), 0)
        # refresh the progress object
        prog = ScriptProgress.objects.get(connection=connection)
        self.assertEquals(prog.step.order, 0)
        self.assertEquals(prog.status, 'P')

        self.elapseTime(prog, 3601)
        response = check_progress(connection)
        self.assertEquals(response, 'First question: what is your favorite way to be spammed?  Be DESCRIPTIVE')
        # refresh the progress object
        prog = ScriptProgress.objects.get(connection=connection)
        self.assertEquals(prog.step.order, 1)
        self.assertEquals(prog.status, 'P')

        #user message error

        # wait a day, with no response
        self.elapseTime(prog, 86401)
        response = check_progress(connection)
        self.assertEquals(response, 'Second question: Do you like CHEESE?')
        prog = ScriptProgress.objects.get(connection=connection)
        self.assertEquals(prog.step.order, 2)
        self.assertEquals(prog.status, 'P')

        # manually move to the next step
        prog.step = ScriptStep.objects.get(order=3)
        prog.status = 'P'
        prog.save()
        self.elapseTime(prog, 2)
        response = check_progress(connection)
        # we've manually moved to the next step, which should merely close the script
        # and delete from ScriptProgress
        self.assertEquals(response, None)
        self.assertEquals(ScriptProgress.objects.count(), 0)
        
        # make sure the ScriptSession table is still correct
        self.assertEquals(ScriptSession.objects.count(), 1)
        self.assertEquals(ScriptSession.objects.all()[0].responses.count(), 0)

    def testIncomingProgress(self):
        connection = Connection.objects.all()[0]
        script = Script.objects.all()[0]
        step = ScriptStep.objects.get(order=1)
        prog = ScriptProgress.objects.create(connection=connection, script=script, step=step, status='P')

        # create a dummy session
        session = ScriptSession.objects.create(connection=connection, script=script)
        incomingmessage = self.fakeIncoming('I like all forms of spam, but typically Nigerian email spam is the best.')
        incoming_progress(incomingmessage)
        self.assertEquals(Response.objects.count(), 1)
        self.assertEquals(ScriptSession.objects.count(), 1)
        self.assertEquals(ScriptSession.objects.all()[0].responses.count(), 1)

        # refresh progress
        prog = ScriptProgress.objects.get(connection=connection)
        self.assertEquals(prog.step.order, 1)
        self.assertEquals(prog.status, 'C')

        # manually move to next step, check_progress would do this
        prog.step = ScriptStep.objects.get(order=2)
        prog.status = 'P'
        prog.save()

        incomingmessage = self.fakeIncoming('Jack cheese is a cheese that I like')
        response_message = incoming_progress(incomingmessage)
        self.assertEquals(response_message, "We didn't understand your response and it's very important to know about your cheese desires.  Please resend.")
        self.assertEquals(Response.objects.count(), 2)

        # refresh progress
        prog = ScriptProgress.objects.get(connection=connection)
        # check that this erroneous poll response didn't update the progress
        r = Response.objects.order_by('-date')[0]
        self.failUnless(r.has_errors)
        self.assertEquals(prog.step.order, 2)
        self.assertEquals(prog.status, 'P')

        incomingmessage = self.fakeIncoming('YES I like jack cheese you silly poll!!!eleventyone')
        response_message = incoming_progress(incomingmessage)
        self.assertEquals(response_message, "It's very good to know that you like cheese!")
        r = Response.objects.order_by('-date')[0]
        self.failIf(r.has_errors)
        self.assertEquals(Response.objects.count(), 3)

        # refresh progress
        prog = ScriptProgress.objects.get(connection=connection)
        # check that this correct poll response updated the progress
        self.assertEquals(prog.step.order, 2)
        self.assertEquals(prog.status, 'C')

    def testLenient(self):
        step = ScriptStep.objects.get(order=2)
        # modify setUp() ScriptStep 2 to be LENIENT
        step.rule = ScriptStep.LENIENT
        step.save()

        # dummy progress, the question for step two has been sent out, now we check
        # that any response (even erroneous) advances progress
        connection = Connection.objects.all()[0]
        script = Script.objects.all()[0]
        step = ScriptStep.objects.get(order=2)
        prog = ScriptProgress.objects.create(connection=connection, script=script, step=step, status='P')
        # create a dummy session
        session = ScriptSession.objects.create(connection=connection, script=script)
        incomingmessage = self.fakeIncoming('Jack cheese is a cheese that I like')
        response_message = incoming_progress(incomingmessage)
        self.assertEquals(response_message, "We didn't understand your response and it's very important to know about your cheese desires.  Please resend.")
        self.assertEquals(Response.objects.count(), 1)

        # refresh progress
        prog = ScriptProgress.objects.get(connection=connection)
        # check that this erroneous poll response DID update the progress,
        # since the rule is now lenient
        r = Response.objects.order_by('-date')[0]
        self.failUnless(r.has_errors)
        self.assertEquals(prog.step.order, 2)
        self.assertEquals(prog.status, 'C')

    def waitFlow(self, giveup = False):
        step = ScriptStep.objects.get(order=2)
        if giveup:
            step.rule = ScriptStep.WAIT_GIVEUP
        else:
            step.rule = ScriptStep.WAIT_MOVEON
        step.giveup_offset = 3600
        step.save()

        # dummy progress, the question for step two has been sent out, now we check
        # that any response (even erroneous) advances progress
        connection = Connection.objects.all()[0]
        script = Script.objects.all()[0]
        prog = ScriptProgress.objects.create(connection=connection, script=script, step=step, status='P')
        session = ScriptSession.objects.create(connection=connection, script=script)
        # elapse past the moveon time
        self.elapseTime(prog, 3601)
        check_progress(connection)
        # refresh progress
        if giveup:
            self.assertEquals(ScriptProgress.objects.count(), 0)
        else:
            prog = ScriptProgress.objects.get(connection=connection)
            self.assertEquals(prog.step.order, 2)
            self.assertEquals(prog.status, 'C')

            # elapse past the start time of the next step
            self.elapseTime(prog, 3610)
            response = check_progress(connection)
            self.assertEquals(response, prog.step.script.steps.get(order=3).message)

            prog = ScriptProgress.objects.get(connection=connection)
            self.assertEquals(prog.step.order, 3)
            self.assertEquals(prog.status, 'P')

    def resendFlow(self, giveup = False):
        script = Script.objects.all()[0]
        connection = Connection.objects.all()[0]
        step = ScriptStep.objects.get(order=2)
        if giveup:
            step.rule = ScriptStep.RESEND_GIVEUP
        else:
            step.rule = ScriptStep.RESEND_MOVEON
        step.retry_offset = 60
        step.giveup_offset = 3600
        step.num_tries = 2
        step.save()
        prog = ScriptProgress.objects.create(connection=connection, script=script, step=step, status='P')
        session = ScriptSession.objects.create(connection=connection, script=script)
        self.elapseTime(prog, 61)
        response = check_progress(connection)
        self.assertEquals(response, "Second question: Do you like CHEESE?")

        # refresh progress
        prog = ScriptProgress.objects.get(connection=connection)
        self.assertEquals(prog.step.order, 2)
        self.assertEquals(prog.status, 'P')
        self.assertEquals(prog.num_tries, 1)

        self.elapseTime(prog, 61)
        response = check_progress(connection)
        self.assertEquals(response, "Second question: Do you like CHEESE?")

        # refresh progress
        prog = ScriptProgress.objects.get(connection=connection)
        self.assertEquals(prog.step.order, 2)
        self.assertEquals(prog.status, 'P')
        self.assertEquals(prog.num_tries, 2)

        # check that we only retry twice
        prog = ScriptProgress.objects.get(connection=connection)
        self.elapseTime(prog, 61)
        response = check_progress(connection)
        self.assertEquals(response, None)

        # elapse past the giveup time
        prog = ScriptProgress.objects.get(connection=connection)
        self.elapseTime(prog, 3600)
        response = check_progress(connection)

        if giveup:
            self.assertEquals(ScriptProgress.objects.count(), 0)
        else:
            self.assertEquals(response, None)
            prog = ScriptProgress.objects.get(connection=connection)
            self.assertEquals(prog.step.order, 2)
            self.assertEquals(prog.status, 'C')

            # elapse past the start time of the next step
            self.elapseTime(prog, 3610)
            response = check_progress(connection)
            self.assertEquals(response, prog.step.script.steps.get(order=3).message)

            prog = ScriptProgress.objects.get(connection=connection)
            self.assertEquals(prog.step.order, 3)
            self.assertEquals(prog.status, 'P')

    def testWaitMoveon(self):
        self.waitFlow()

    def testResendMoveon(self):
        self.resendFlow()

    def testWaitGiveup(self):
        self.waitFlow(giveup=True)

    def testResendGiveup(self):
        self.resendFlow(giveup=True)

    #test signals
    def testScriptSignals(self):
        connection = Connection.objects.all()[0]
        script = Script.objects.all()[0]
        prog = ScriptProgress.objects.create(connection=connection, script=script)
        prog.step= ScriptStep.objects.get(order=2)
        prog.save()
        n_step=ScriptStep.objects.get(order=3)
        #call back
        def receive(sender, **kwargs):
            self.assertEqual(kwargs['connection'].pk, connection.pk)
            #self.assertEqual(kwargs['step'],n_step)
            received_signals.append(kwargs.get('signal'))
        # Connect signals and keep track of handled ones
        received_signals = []
        expected_signals=[script_progress_pre_change,script_progress]
        for signal in expected_signals:
            signal.connect(receive,weak=False)
        prog.move_to_nextstep()
        self.assertEqual(received_signals, expected_signals)

    def assertProgress(self, connection, step_num, step_status, session_count, response_count):
        progress = ScriptProgress.objects.get(connection=connection)
        script = Script.objects.all()[0]
        if step_num is not None:
            step = script.steps.get(order=step_num)
            self.assertEquals(progress.step, step)
        else:
            self.assertEquals(progress.step, None)
        self.assertEquals(ScriptSession.objects.count(), session_count)
        if session_count:
            self.assertEquals(ScriptSession.objects.all()[0].responses.count(), response_count)
        self.assertEquals(Response.objects.count(), response_count)
        # return the refreshed progress
        return progress

    def testFullScriptFlow(self):
        script = Script.objects.all()[0]
        connection = Connection.objects.all()[0]
        progress = ScriptProgress.objects.create(connection=connection, script=script)

        # test that an incoming message from a user freshly added to the script
        # (i.e., no call to check_progress yet) doesn't fail
        incomingmessage = self.fakeIncoming('Im in the script, but nothings happened yet.  What next?')
        response_message = incoming_progress(incomingmessage)
        # no response message
        self.assertEquals(response_message, None)
        # refresh progress, no updates to progress should be made
        # no ScriptSession should be created, that's up to check_progress
        progress = self.assertProgress(connection, None, '', 0, 0)

        # modify step 1, check_progress should wait a full minute before sending out
        # the first message
        step0 = script.steps.get(order=0)
        step0.start_offset = 60
        step0.save()

        response = check_progress(connection)
        # we're still waiting to send the first message, for a full minute
        self.assertEquals(response, None)
        self.elapseTime(progress, 60)

        response = check_progress(connection)
        # we're ready for the first message to go out
        self.assertEquals(response, step0.message)
        # refresh progress
        # we should now be advanced to step 0, in 'P'ending status
        # because it's a WAIT_MOVEON step, so we have to wait for one
        # hour before advancing to the next step
        # there should be a scriptsession at this point
        # but there shouldn't be any responses
        progress = self.assertProgress(connection, 0, 'P', 1, 0)

        # test that an incoming message from a user in this portion
        # of the script doesn't affect the progress
        incomingmessage = self.fakeIncoming('Im in the script, but Im waiting to be asked a question.  Why do I have to wait for an hour?')
        response_message = incoming_progress(incomingmessage)
        # no response message
        self.assertEquals(response_message, None)
        # refresh progress
        # no updates to progress
        # there should still be a scriptsession, but only one
        # and there still shouldn't be any responses
        progress = self.assertProgress(connection, 0, 'P', 1, 0)

        # now let's wait a full hour
        self.elapseTime(progress, 3600)
        step1 = script.steps.get(order=1)
        response = check_progress(connection)
        # the first poll question should go out now
        self.assertEquals(response, step1.poll.question)
        # refresh progress
        # check that the step is now step 1, with status 'P'
        # there should still be a scriptsession, but only one
        # and there still shouldn't be any responses
        progress = self.assertProgress(connection, 1, 'P', 1, 0)

        # check that an additional call to check_progress doesn't re-send the
        # question
        response = check_progress(connection)
        # the first poll question should go out now
        self.assertEquals(response, None)
        # check that the step is still step 1, with status 'P'
        # there should still be a scriptsession, but only one
        # and there still shouldn't be any responses
        progress = self.assertProgress(connection, 1, 'P', 1, 0)

        # test the moveon scenario, wait a full day with no response
        self.elapseTime(progress, 86400)
        # make sure that incoming_progress respects the giveup time of
        # the previous step and drops any messages (otherwise it's a
        # potential race contidion
        incomingmessage = self.fakeIncoming('I like spam, Im just a little late to mention anything about it')
        response_message = incoming_progress(incomingmessage)
        self.assertEquals(response, None)
        progress = self.assertProgress(connection, 1, 'P', 1, 0)
        # check that this call to check_progress sends out the
        # next question
        response = check_progress(connection)
        step2 = script.steps.get(order=2)
        # the first poll question should go out now
        self.assertEquals(response, step2.poll.question)
        # check that the step is now step 2, with status 'P'
        # there should still be a scriptsession, but only one
        # and there still shouldn't be any responses
        progress = self.assertProgress(connection, 2, 'P', 1, 0)

        # test the scenario where a response is received
        progress.step = step1
        progress.status = 'P'
        progress.save()
        session = ScriptSession.objects.all()[0]
        session.start_time = datetime.datetime.now()
        session.end_time = None
        for r in session.responses.all():
            r.delete()
        for r in Response.objects.all():
            r.delete()
        session.save()

        # test that an incoming message from a user in this portion
        # of the script affects the progress
        step1response = 'My favorite form of spam is an overabundance of test cases ;-)'
        incomingmessage = self.fakeIncoming(step1response)
        response_message = incoming_progress(incomingmessage)
        self.failUnless(response_message == None or response_message == '')
        # we should move the status of step 1 to complete, and there should
        # be one response in the ScriptSession
        progress = self.assertProgress(connection, 1, 'C', 1, 1)
        # test that the response was processed correctly
        self.assertEquals(Response.objects.all()[0].pk, ScriptSession.objects.all()[0].responses.all()[0].response.pk)
        self.assertEquals(Response.objects.all()[0].eav.poll_text_value, step1response)

        # check that this call to check_progress sends out the
        # next question
        response = check_progress(connection)
        # the first poll question should go out now
        self.assertEquals(response, step2.poll.question)
        # check that the step is now step 2, with status 'P'
        # there should still be a scriptsession, but only one
        # and there still should be one response
        progress = self.assertProgress(connection, 2, 'P', 1, 1)

        # no movement until we get a response this time
        response = check_progress(connection)
        self.assertEquals(response, None)
        progress = self.assertProgress(connection, 2, 'P', 1, 1)

        step2errorResponse = 'I like cheese'
        incomingmessage = self.fakeIncoming(step2errorResponse)
        response_message = incoming_progress(incomingmessage)
        self.assertEquals(response_message, step2.poll.categories.get(name='unknown').response)
        # we should be in the same step, with one additional response
        progress = self.assertProgress(connection, 2, 'P', 1, 2)

        # no movement until we get a response this time
        response = check_progress(connection)
        self.assertEquals(response, None)
        progress = self.assertProgress(connection, 2, 'P', 1, 2)

        step2yesResponse = 'YES I like cheese'
        incomingmessage = self.fakeIncoming(step2yesResponse)
        response_message = incoming_progress(incomingmessage)
        self.assertEquals(response_message, step2.poll.categories.get(name='yes').response)
        # we should be in the same step, with one additional response and 'C'omplete status
        progress = self.assertProgress(connection, 2, 'C', 1, 3)

        # no movement until for a full hour
        response = check_progress(connection)
        self.assertEquals(response, None)
        progress = self.assertProgress(connection, 2, 'C', 1, 3)

        # incoming messages shouldn't do anything here
        # (in fact, the shouldn't be added even as responses to the poll, since
        # the status of this step is complete)
        incomingmessage = self.fakeIncoming('still just waiting around for another message')
        response_message = incoming_progress(incomingmessage)
        self.failUnless(response_message == None or response_message == '')
        progress = self.assertProgress(connection, 2, 'C', 1, 3)

        # wait an hour
        self.elapseTime(progress, 3601)
        step3 = script.steps.get(order=3)
        # this should complete the script
        response = check_progress(connection)
        self.assertEquals(response, step3.message)
        progress = self.assertProgress(connection, 3, 'P', 1, 3)

        # incoming messages shouldn't do anything here
        # (in fact, the shouldn't be added even as responses to the poll, since
        # the status of this step is complete)
        incomingmessage = self.fakeIncoming('im done with the script, just sending random stuff')
        response_message = incoming_progress(incomingmessage)
        self.failUnless(response_message == None or response_message == '')
        progress = self.assertProgress(connection, 3, 'P', 1, 3)

        # wait a few more seconds, then check that the script is closed out
        self.elapseTime(progress, 10)
        response = check_progress(connection)
        self.assertEquals(response, None)
        self.assertEquals(ScriptProgress.objects.count(), 0)
        self.assertEquals(ScriptSession.objects.all()[0].responses.count(), 3)
        self.failIf(ScriptSession.objects.all()[0].end_time is None)
