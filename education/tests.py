"""
Basic tests for Edtrac
"""
from django.test import TestCase
from django.utils import unittest
from django.db.models.signals import post_syncdb
from rapidsms.messages.incoming import IncomingMessage, OutgoingMessage
from rapidsms_xforms.models import *
from rapidsms_httprouter.models import Message
from rapidsms.contrib.locations.models import Location, LocationType
import datetime
from rapidsms.models import Connection, Backend, Contact
from rapidsms_xforms.models import XForm, XFormSubmission
from django.conf import settings
from script.utils.outgoing import check_progress
from script.models import Script, ScriptProgress, ScriptSession, ScriptResponse, ScriptStep
from education.management import *
from rapidsms_httprouter.router import get_router
from script.signals import script_progress_was_completed, script_progress
from poll.management import create_attributes
from education.models import EmisReporter, School, reschedule_weekly_polls, reschedule_monthly_polls, reschedule_termly_polls, reschedule_midterm_polls
from django.db import connection
from script.utils.outgoing import check_progress
from django.core.management import call_command
from unregister.models import Blacklist
from education.utils import _next_thursday, _date_of_monthday, _next_midterm, _next_term_question_date
from poll.models import ResponseCategory
from .models import match_group_response
from script.utils.handling import find_best_response
from django.test.client import Client
import difflib

class ModelTest(TestCase): #pragma: no cover
    fixtures = ['edtrac_data.json']
    # Model tests
    def setUp(self):
        
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            site_id = getattr(settings, 'SITE_ID', 5)
            Site.objects.get_or_create(pk=site_id, defaults={'domain':'rapidemis.com'})

        User.objects.get_or_create(username='admin')
        self.backend = Backend.objects.create(name='test')
        self.connection = Connection.objects.create(identity='8675309', backend=self.backend)
        country = LocationType.objects.create(name='country', slug='country')
        district = LocationType.objects.create(name='district', slug='district')
        subcounty = LocationType.objects.create(name='sub_county', slug='sub_county')
        self.root_node = Location.objects.create(type=country, name='Uganda')
        self.kampala_district = Location.objects.create(type=district, name='Kampala')
        self.kampala_subcounty = Location.objects.create(type=subcounty, name='Kampala')
        self.gulu_subcounty = Location.objects.create(type=subcounty, name='Gulu')
        self.gulu_school = School.objects.create(name="St. Mary's", location=self.gulu_subcounty)
        self.kampala_school = School.objects.create(name="St. Mary's", location=self.kampala_subcounty)
        self.kampala_school2 = School.objects.create(name="St. Peters", location=self.kampala_district)
        self.kampala_school3 = School.objects.create(name="St. Mary's", location=self.kampala_district)

    def fake_incoming(self, message, connection=None):
        if connection is None:
            connection = self.connection
        router = get_router()
        handled = router.handle_incoming(connection.backend.name, connection.identity, message)
        return handled
    #        return router.handle_incoming(connection.backend.name, connection.identity, message)
    #        form = XForm.find_form(message)
    #        incoming_message = IncomingMessage(connection, message)
    #        incoming_message.db_message = Message.objects.create(direction="I", connection=connection, text=message)
    #        if form:
    #            submission = form.process_smc_submission(
    #
    #            )
    #            return XFormSubmission.objects.all().order_by('-created')[0]


    def spoof_incoming_obj(self, message, connection=None):
        if connection is None:
            connection = Connection.objects.all()[0]
        incomingmessage = IncomingMessage(connection, message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=Connection.objects.all()[0], text=message)
        return incomingmessage


    def assertResponseEquals(self, message, expected_response, connection=None):
        s = self.fake_incoming(message, connection)
        self.assertEquals(s.response, expected_response)


    def fake_submission(self, message, connection=None):
        form = XForm.find_form(message)
        if connection is None:
            try:
                connection = Connection.objects.all()[0]
            except IndexError:
                backend, created = Backend.objects.get_or_create(name='test')
                connection, created = Connection.objects.get_or_create(identity='8675309',
                    backend=backend)
                # if so, process it
        incomingmessage = IncomingMessage(connection, message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=connection, text=message)
        if form:
            submission = form.process_sms_submission(incomingmessage)
            return submission
        return None


    def fake_error_submission(self, message, connection=None):
        form = XForm.find_form(message)

        if connection is None:
            connection = Connection.objects.all()[0]
            # if so, process it
        incomingmessage = IncomingMessage(connection, message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=Connection.objects.all()[0], text=message)
        if form:
            submission = form.process_sms_submission(incomingmessage)
            self.failUnless(submission.has_errors)
        return

    def elapseTime(self, submission, seconds):
        newtime = submission.created - datetime.timedelta(seconds=seconds)
        cursor = connection.cursor()
        cursor.execute("update rapidsms_xforms_xformsubmission set created = '%s' where id = %d" %
                       (newtime.strftime('%Y-%m-%d %H:%M:%S.%f'), submission.pk))


    def total_seconds(self, time_delta):
        """
        function to return total seconds in interval (for Python less than 2.7)
        """
        seconds = time_delta.seconds
        days_to_seconds = time_delta.days * 24 * 60 * 60
        return seconds + days_to_seconds


    def elapseTime2(self, progress, seconds):
        """
        This hack mimics the progression of time, from the perspective of a linear test case,
        by actually *subtracting* from the value that's currently stored (usually datetime.datetime.now())
        """
        progress.set_time(progress.time - datetime.timedelta(seconds=seconds))
        try:
            session = ScriptSession.objects.get(connection=progress.connection, script__slug=progress.script.slug, end_time=None)
            session.start_time = session.start_time - datetime.timedelta(seconds=seconds)
            session.save()
        except ScriptSession.DoesNotExist:
            pass

    def fake_script_dialog(self, script_prog, connection, responses, emit_signal=True):
        script = script_prog.script
        ss = ScriptSession.objects.create(script=script, connection=connection, start_time=datetime.datetime.now())
        for poll_name, resp in responses:
            poll = script.steps.get(poll__name=poll_name).poll
            poll.process_response(self.spoof_incoming_obj(resp, connection))
            resp = poll.responses.all()[0]
            ScriptResponse.objects.create(session=ss, response=resp)
        if emit_signal:
            script_progress_was_completed.send(connection=connection, sender=script_prog)
        return ss

    def register_reporter(self, grp, phone=None):
        connection = Connection.objects.create(identity=phone, backend=self.backend) if phone else self.connection
        self.fake_incoming('join', connection)
        script_prog = ScriptProgress.objects.filter(script__slug='edtrac_autoreg').order_by('-time')[0]

#        params = [
#            ('edtrac_role', grp, ['all']),\
#            ('edtrac_gender', 'male', ['Head Teachers']),\
#            ('edtrac_class', 'p3', ['Teachers']),\
#            ('edtrac_district', 'kampala', ['all']),\
#            ('edtrac_subcounty', 'kampala', ['all']),\
#            ('edtrac_school', 'st. marys', ['Teachers', 'Head Teachers', 'SMC']),\
#            ('edtrac_name', 'testy mctesterton', ['all']),\
#        ]
        params = [
            ('edtrac_role', grp, ['all']),\
            ('edtrac_gender', 'male', ['2']),\
            ('edtrac_class', 'p3', ['1']),\
            ('edtrac_district', 'kampala', ['all']),\
            ('edtrac_subcounty', 'kampala', ['all']),\
            ('edtrac_school', 'st. marys', ['1', '2', '3']),\
            ('edtrac_name', 'testy mctesterton', ['all']),\
        ]
        param_list = []
        for step_name, value, grps in params:
            g = difflib.get_close_matches(grp, grps, 1, 0.8)
            if grps[0] == 'all':
                param_list.append((step_name, value))
            elif len(g)>0:
                param_list.append((step_name, value))
            else:
                pass
        self.fake_script_dialog(script_prog, connection, param_list)

    def ask_for_data(self, connection = None, script_slug = None):
        """
        This function is used to ask for data or a response to polls that weren't answered. It can be turned on like
        a switch.
        """
        if (connection is not None) and (script_slug is not None):
            # get existing script with script slug
            script = Script.objects.get(slug = script_slug)
            # setup script
            # create a random ScriptProgress to mimic much of the existing ScriptProgress
            ScriptProgress.objects.create(
                connection = connection,
                script = script
            )

    def testBasicAutoReg(self):
        Script.objects.filter(slug='edtrac_autoreg').update(enabled=True)
        self.register_reporter('1')
        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.kampala_subcounty)
        self.assertEquals(contact.schools.all()[0], self.kampala_school)
        self.assertEquals(contact.groups.all()[0].name, 'Teachers')
        self.assertEquals(contact.grade, 'P3')
        self.assertEquals(contact.gender, None)
        self.assertEquals(contact.default_connection, self.connection)
        self.assertEquals(ScriptProgress.objects.filter(connection=self.connection).count(), 2)
        self.assertListEqual(list(ScriptProgress.objects.filter(connection=self.connection).values_list('script__slug', flat=True)), ['edtrac_autoreg', 'edtrac_teachers_weekly'])

    def testBadAutoReg(self):
        """
        Crummy answers
        """
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('edtrac_role', 'bodaboda'),\
            ('edtrac_district', 'kampala'),\
            ('edtrac_subcounty', 'amudat'),\
            ('edtrac_name', 'bad tester'),\
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.groups.all()[0].name, 'Other Reporters')
        self.assertEquals(contact.reporting_location, self.kampala_district)

    def testAutoRegNoLocationData(self):

        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('edtrac_role', '1'),\
            ('edtrac_name', 'no location data tester'),\
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.reporting_location, self.root_node)

    def testAutoRegNoRoleNoName(self):
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('edtrac_district', 'kampala'),\
            ('edtrac_subcounty', 'Gul'),\
            ('edtrac_school', 'St Marys'),\
        ])
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.groups.all()[0].name, 'Other Reporters')
        self.assertEquals(contact.reporting_location, self.gulu_subcounty)
        self.assertEquals(contact.name, 'Anonymous User')
        #without a role a reporter should not be scheduled for any regular polls
        self.assertListEqual(list(ScriptProgress.objects.filter(connection=self.connection).values_list('script__slug', flat=True)), ['edtrac_autoreg'])

    def testAutoRegNoGrade(self):
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('edtrac_role', '1'),\
            ('edtrac_name', 'no grade tester'),\
            ('edtrac_district', 'kampala'),\
            ('edtrac_subcounty', 'Gul'),\
            ('edtrac_school', 'St Marys'),\
        ])
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.groups.all()[0].name, 'Teachers')
        self.assertEquals(contact.reporting_location, self.gulu_subcounty)
        self.assertEquals(contact.name, 'No Grade Tester')
        #without a grade a reporter should not be scheduled for any regular polls
        self.assertListEqual(list(ScriptProgress.objects.filter(connection=self.connection).values_list('script__slug', flat=True)), ['edtrac_autoreg'])

    def testBasicQuit(self):
        self.register_reporter('1')
        ScriptProgress.objects.filter(script__slug='edtrac_autoreg', connection=self.connection).delete() #script always deletes a connection on completion of registration
        #quit system
        self.fake_incoming('quit')
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, "Thank you for your contribution to EduTrac. To rejoin the system, send join to 6200")
        self.assertEquals(Blacklist.objects.filter(connection=self.connection).count(), 1) #blacklisted
        self.assertEquals(EmisReporter.objects.count(), 1) #the user is not deleted, only blacklisted
        
    def testQuitChangeGroup(self):
        self.register_reporter('1')
        ScriptProgress.objects.filter(script__slug='edtrac_autoreg', connection=self.connection).delete() #script always deletes a connection on completion of registration
        #quit system
        self.fake_incoming('quit')
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, "Thank you for your contribution to EduTrac. To rejoin the system, send join to 6200")
        self.assertEquals(Blacklist.objects.filter(connection=self.connection).count(), 1) #blacklisted
        self.assertEquals(EmisReporter.objects.count(), 1) #the user is not deleted, only blacklisted
        
        #Now lets join as and change group, group should change, each user should be attached to one and only one group
        Script.objects.filter(slug='edtrac_autoreg').update(enabled=True) #First enable the autoreg script if its not enabled
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=0).poll.question)
        self.fake_incoming('2')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=1).poll.question)
        self.assertNotEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=2).poll.question)
        self.fake_incoming('Male')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=3).poll.question)
        self.fake_incoming('Kampala')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=4).poll.question)
        self.fake_incoming('Kampala')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=5).poll.question)
        self.fake_incoming('St. Marys')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=6).poll.question)
        self.fake_incoming('test mctester')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=7).message)
        self.elapseTime2(script_prog, 1)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(EmisReporter.objects.count(), 1) #we still have only one user in the system, same user who quit and rejoined
        self.assertEquals(EmisReporter.objects.all()[0].groups.count(), 1) #user retains on one group
        self.assertEquals(EmisReporter.objects.all()[0].groups.all()[0].name, Group.objects.filter(name='Head Teachers')[0].name) #group has changed

    def testDoubleReg(self):

        #join again when already in the process of registration
        self.fake_incoming('join')
        self.fake_incoming('join')
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, "Your registration is not complete yet, you do not need to 'Join' again.")

        #cleanout scriptprogress and register again
        ScriptProgress.objects.filter(script__slug='edtrac_autoreg', connection=self.connection).delete()
        self.register_reporter('1')
        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.kampala_subcounty)
        self.assertEquals(contact.schools.all()[0], self.kampala_school)
        self.assertEquals(contact.groups.all()[0].name, 'Teachers')

        self.fake_incoming('join')
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, "You are already in the system and do not need to 'Join' again.")
        self.assertEquals(ScriptProgress.objects.filter(script__slug='edtrac_autoreg').count(), 1)

    def testQuitRejoin(self):
        #first join
        self.register_reporter('1')
        self.assertEquals(EmisReporter.objects.count(), 1)
        #when a user sucessfully registers, their registration is expunged from script progress
        ScriptProgress.objects.filter(script__slug='edtrac_autoreg', connection=self.connection).delete()

        #then quit
        self.fake_incoming('quit')
        self.assertEquals(Blacklist.objects.all()[0].connection, self.connection)
        self.assertEquals(EmisReporter.objects.all()[0].active, False)

        self.register_reporter('1')
        self.assertEquals(EmisReporter.objects.count(), 1)

    def testQuitIncompleteRegistration(self):
        #first join
        self.fake_incoming('join')
        self.assertEquals(ScriptProgress.objects.filter(script__slug='edtrac_autoreg', connection=self.connection).count(), 1)

        #then quit
        self.fake_incoming('quit')
        self.assertEquals(Blacklist.objects.count(), 0)
        #notify user to first complete current registration
        self.assertEquals(Message.objects.all().order_by('-date')[0].text, 'Your registration is not complete, you can not quit at this point')
        #their current registration process is still valid
        self.assertEquals(ScriptProgress.objects.filter(script__slug='edtrac_autoreg', connection=self.connection).count(), 1)

    def testGemAutoReg(self):
        self.fake_incoming('join')
        self.assertEquals(ScriptProgress.objects.count(), 1)
        script_prog = ScriptProgress.objects.all()[0]
        self.assertEquals(script_prog.script.slug, 'edtrac_autoreg')

        self.fake_script_dialog(script_prog, self.connection, [\
            ('edtrac_role', '4'),\
            ('edtrac_district', 'kampala'),\
            ('edtrac_name', 'testy mctesterton'),\
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.kampala_district)
        self.assertEquals(contact.groups.all()[0].name, 'GEM')
        self.assertEquals(ScriptProgress.objects.filter(connection=self.connection).count(), 2)
        self.assertListEqual(list(ScriptProgress.objects.filter(connection=self.connection).values_list('script__slug', flat=True)), ['edtrac_autoreg', 'edtrac_gem_monthly'])

    def testMeoAutoReg(self):
        self.fake_incoming('join')
        self.assertEquals(ScriptProgress.objects.count(), 1)
        script_prog = ScriptProgress.objects.all()[0]
        self.assertEquals(script_prog.script.slug, 'edtrac_autoreg')

        self.fake_script_dialog(script_prog, self.connection, [\
            ('edtrac_role', '6'),\
            ('edtrac_district', 'kampala'),\
            ('edtrac_name', 'testy mctesterton'),\
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.kampala_district)
        self.assertEquals(contact.groups.all()[0].name, 'MEO')
        self.assertEquals(ScriptProgress.objects.filter(connection=self.connection).count(), 1)
        self.assertListEqual(list(ScriptProgress.objects.filter(connection=self.connection).values_list('script__slug', flat=True)), ['edtrac_autoreg'])
        
    def testTeacherAutoregKannelGetUrl(self):
        get_url = '/router/receive/?password=%s&backend=%s&sender=%s&message=%s'
        msg = 'Join'
        sender = '8675319'
        backend = 'test'
        password = 'p73TestP'
        c = Client()
        Script.objects.filter(slug='edtrac_autoreg').update(enabled=True)
        
        resp = c.get(get_url % (password, backend, sender, msg))
        script_prog = ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=0).poll.question)
        c.get(get_url % (password, backend, sender, '1'))
        script_prog = ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        print Message.objects.all()
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=2).poll.question)

    def testTeacherAutoregProgression(self):
        Script.objects.filter(slug='edtrac_autoreg').update(enabled=True)
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=0).poll.question)
        self.fake_incoming('1')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertNotEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=1).poll.question)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=2).poll.question)
        self.fake_incoming('P3')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=3).poll.question)
        self.fake_incoming('Kampala')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=4).poll.question)
        self.fake_incoming('Kampala')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=5).poll.question)
        self.fake_incoming('St. Marys')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=6).poll.question)
        self.fake_incoming('test mctester')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 61)
        call_command('check_script_progress', e=8, l=24)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=7).message)

    def testSMCAutoregProgression(self):
        Script.objects.filter(slug='edtrac_autoreg').update(enabled=True)
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=0).poll.question)
        self.fake_incoming('3')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=3).poll.question)
        self.fake_incoming('Kampala')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=4).poll.question)
        self.fake_incoming('Kampala')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=5).poll.question)
        self.fake_incoming('St. Marys')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=6).poll.question)
        self.fake_incoming('test mctester')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=7).message)

    def testGEMAutoregProgression(self):
        Script.objects.filter(slug='edtrac_autoreg').update(enabled=True)
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=0).poll.question)
        self.fake_incoming('4')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=3).poll.question)
        self.fake_incoming('Kampala')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=4).poll.question)
        self.fake_incoming('Kampala')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=6).poll.question)
        self.fake_incoming('test mctester')
        script_prog = ScriptProgress.objects.get(connection=self.connection, script__slug='edtrac_autoreg')
        self.elapseTime2(script_prog, 3601)
        check_progress(script_prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_autoreg').steps.get(order=7).message)

    def testNextThursdayReset(self):
        """
        Test that regardless of day of the week, _next_thursday() always
        returns a Thursday at 10 oclock
        """
        
        d = datetime.datetime.now()
        nt = _next_thursday()
        self.assertEquals(3, nt.weekday())
        self.assertEquals(10, nt.hour)
        for x in range(0, 7):
            set_time = d + datetime.timedelta(days=x)
            print _next_thursday(set_time=set_time)
            self.assertEquals(3, _next_thursday(set_time=set_time).weekday()) 
            self.assertEquals(10, _next_thursday(set_time=set_time).hour) 
            
    def testRoleAssignment(self):
        """
        Test the multiple response role question, it should match 
        the provided response option to the appropriate grup
        """
        #Option 1 should be matched to teachers
        self.register_reporter('1')
        prog = ScriptProgress.objects.get(script__slug='edtrac_autoreg', connection=self.connection)
        session = ScriptSession.objects.filter(script=prog.script, connection=self.connection).order_by('-end_time')[0]
        role_poll = prog.script.steps.get(poll__name='edtrac_role').poll
        role = find_best_response(session, role_poll)
        group = match_group_response(session, role, role_poll)
        self.assertEquals(group.name, "Teachers")
        
        #Option 2 should be matched to head teachers
        self.register_reporter('2', '8675319')
        prog = ScriptProgress.objects.get(script__slug='edtrac_autoreg', connection__identity='8675319')
        session = ScriptSession.objects.filter(script=prog.script, connection__identity='8675319').order_by('-end_time')[0]
        role_poll = prog.script.steps.get(poll__name='edtrac_role').poll
        role = find_best_response(session, role_poll)
        group = match_group_response(session, role, role_poll)
        self.assertEquals(group.name, "Head Teachers")
        
        #Option 3 should be matched to SMC
        self.register_reporter('3', '8675329')
        prog = ScriptProgress.objects.get(script__slug='edtrac_autoreg', connection__identity='8675329')
        session = ScriptSession.objects.filter(script=prog.script, connection__identity='8675329').order_by('-end_time')[0]
        role_poll = prog.script.steps.get(poll__name='edtrac_role').poll
        role = find_best_response(session, role_poll)
        group = match_group_response(session, role, role_poll)
        self.assertEquals(group.name, "SMC")
        
        #Option 4 should be matched to GEM
        self.register_reporter('4', '8675339')
        prog = ScriptProgress.objects.get(script__slug='edtrac_autoreg', connection__identity='8675339')
        session = ScriptSession.objects.filter(script=prog.script, connection__identity='8675339').order_by('-end_time')[0]
        role_poll = prog.script.steps.get(poll__name='edtrac_role').poll
        role = find_best_response(session, role_poll)
        group = match_group_response(session, role, role_poll)
        self.assertEquals(group.name, "GEM")
        
        #Option 5 should be matched to DEO
        self.register_reporter('5', '8675349')
        prog = ScriptProgress.objects.get(script__slug='edtrac_autoreg', connection__identity='8675349')
        session = ScriptSession.objects.filter(script=prog.script, connection__identity='8675349').order_by('-end_time')[0]
        role_poll = prog.script.steps.get(poll__name='edtrac_role').poll
        role = find_best_response(session, role_poll)
        group = match_group_response(session, role, role_poll)
        self.assertEquals(group.name, "DEO")
        
        #Option 6 should be matched to MEO
        self.register_reporter('6', '8675359')
        prog = ScriptProgress.objects.get(script__slug='edtrac_autoreg', connection__identity='8675359')
        session = ScriptSession.objects.filter(script=prog.script, connection__identity='8675359').order_by('-end_time')[0]
        role_poll = prog.script.steps.get(poll__name='edtrac_role').poll
        role = find_best_response(session, role_poll)
        group = match_group_response(session, role, role_poll)
        self.assertEquals(group.name, "MEO")
        
        #Unknown Option should be matched to "Other Reporters
        self.register_reporter('7', '8675369')
        prog = ScriptProgress.objects.get(script__slug='edtrac_autoreg', connection__identity='8675369')
        session = ScriptSession.objects.filter(script=prog.script, connection__identity='8675369').order_by('-end_time')[0]
        role_poll = prog.script.steps.get(poll__name='edtrac_role').poll
        role = find_best_response(session, role_poll)
        group = match_group_response(session, role, role_poll)
        self.assertEquals(group.name, "Other Reporters")
        
            
#Weekly Polls, tests
#Teachers
    def testWeeklyTeacherPolls(self):
        self.register_reporter('1')
        Script.objects.filter(slug__in=['edtrac_teachers_weekly', 'edtrac_teachers_monthly']).update(enabled=True)
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        seconds_to_thursday = self.total_seconds(_next_thursday() - datetime.datetime.now())
        self.elapseTime2(prog, seconds_to_thursday+(1*60*60)) #seconds to thursday + one hour
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=0).poll.question)
        self.fake_incoming('40')
        self.assertEquals(Message.objects.filter(direction='I').order_by('-date')[0].application, 'script')
        self.assertEquals(Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=0).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 40)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=2).poll.question)
        self.fake_incoming('55girls')
        self.fake_incoming('65girls') # proof that the last instantaneous response is not equal to 65
        self.assertEquals(Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=2).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 55)
        self.assertNotEquals(Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=2).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 65)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=4).poll.question)
        self.fake_incoming('3')
        self.assertEquals(Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=4).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 3)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        check_progress(prog.script)
        # a whole new progress might be created??
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).__unicode__(), 'Not Started')
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time, _next_thursday())
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time.hour, 10)

    def testTermlyHeadTeacherSpecialPolls(self):
        #TODO add testing for special script poll (views testing)
        self.testTermlyHeadTeacherPolls()

    def playTimeTrick(self, progress):
        time = progress.time
        now = datetime.datetime.now()
        return self.total_seconds(time - now)

#Head Teachers Weekly
    def testWeeklyHeadTeacherPolls(self):
        self.register_reporter('2')
        Script.objects.filter(slug__in=['edtrac_head_teachers_weekly', 'edtrac_head_teachers_monthly', 'edtrac_head_teachers_termly']).update(enabled=True)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_weekly', connection=self.connection)
        seconds_to_thursday = self.total_seconds(_next_thursday() - datetime.datetime.now())
        self.elapseTime2(prog, seconds_to_thursday+(1*60*60)) #seconds to thursday + one hour
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_weekly', connection=self.connection)
        check_progress(prog.script); check_progress(prog.script); check_progress(prog.script); check_progress(prog.script); # multiple check_progresses for Head Teacher b'se of question skip
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_weekly').steps.get(order=0).poll.question)
        self.fake_incoming('6')
        self.assertEquals(Message.objects.filter(direction='I').order_by('-date')[0].application, 'script')
        self.assertEquals(Script.objects.get(slug='edtrac_head_teachers_weekly').steps.get(order=0).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 6)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_weekly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_weekly').steps.get(order=1).poll.question)
        self.fake_incoming('5 male teachers')
        self.assertEquals(Script.objects.get(slug='edtrac_head_teachers_weekly').steps.get(order=1).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 5)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_weekly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).__unicode__(), 'Not Started')
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time, _next_thursday())
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time.hour, 10)

#SMC Weekly        
    def testWeeklySMCPolls(self):
        self.register_reporter('3')
        Script.objects.filter(slug__in=['edtrac_smc_weekly', 'edtrac_smc_monthly', 'edtrac_smc_termly']).update(enabled=True)
        prog = ScriptProgress.objects.get(script__slug='edtrac_smc_weekly', connection=self.connection)
        seconds_to_thursday = self.total_seconds(_next_thursday() - datetime.datetime.now())
        self.elapseTime2(prog, seconds_to_thursday+(1*60*60)) #seconds to thursday + one hour
        prog = ScriptProgress.objects.get(script__slug='edtrac_smc_weekly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_smc_weekly').steps.get(order=0).poll.question)
        self.fake_incoming('yes')
        check_progress(prog.script)
        poll = Script.objects.get(slug='edtrac_smc_weekly').steps.get(order=0).poll
        yes_category = poll.categories.filter(name='yes')
        response = poll.responses.all().order_by('-pk')[0]
        self.assertEquals(ResponseCategory.objects.get(response__poll__name=poll.name,  category=yes_category).response, response)
        #script was completed on the previous step and this should throw the next time of asking to _next_thursday()
        check_progress(prog.script)
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).__unicode__(), 'Not Started')
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time, _next_thursday())
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time.hour, 10)


    def testMonthlyHeadTeacherPolls(self):
        self.register_reporter('2')
        Script.objects.filter(slug__in=['edtrac_head_teachers_weekly', 'edtrac_head_teachers_monthly', 'edtrac_head_teachers_termly']).update(enabled=True)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_monthly', connection=self.connection)
        d = _date_of_monthday('last')
        seconds_to_lastday = self.total_seconds(d - datetime.datetime.now())
        self.elapseTime2(prog, seconds_to_lastday+(1*60*60)) #seconds to last day of month + one hour
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_monthly', connection=self.connection)
        self.assertEquals(prog.script.steps.count(), 2)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_monthly').steps.get(order=0).poll.question)
        self.fake_incoming('5')
        self.assertEquals(Message.objects.filter(direction='I').order_by('-date')[0].application, 'script')
        self.assertEquals(Script.objects.get(slug='edtrac_head_teachers_monthly').steps.get(order=0).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 5)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_monthly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_monthly').steps.get(order=1).poll.question)
        self.fake_incoming('25%')
        self.assertEquals(Message.objects.filter(direction='I').order_by('-date')[0].application, 'script')
        self.assertEquals(Script.objects.get(slug='edtrac_head_teachers_monthly').steps.get(order=1).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 25)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_monthly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).__unicode__(), 'Not Started')
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time.hour, 10)
        seconds_to_nextprog = self.total_seconds(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time - datetime.datetime.now())
        seconds_to_monthday = self.total_seconds(_date_of_monthday('last') - datetime.datetime.now())
        self.assertEquals(seconds_to_nextprog, seconds_to_monthday)
        
    def testMonthlySMCPolls(self):
        self.register_reporter('3')
        Script.objects.filter(slug__in=['edtrac_smc_weekly', 'edtrac_smc_monthly', 'edtrac_smc_termly']).update(enabled=True)
        prog = ScriptProgress.objects.get(script__slug='edtrac_smc_monthly', connection=self.connection)
        d = _date_of_monthday(5)
        seconds_to_5th = self.total_seconds(d - datetime.datetime.now())
        self.elapseTime2(prog, seconds_to_5th+(1*60*60)) #seconds to 5th + one hour
        prog = ScriptProgress.objects.get(script__slug='edtrac_smc_monthly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_smc_monthly').steps.get(order=0).poll.question)
        self.fake_incoming('50%')
        self.assertEquals(Script.objects.get(slug='edtrac_smc_monthly').steps.get(order=0).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 50)
        prog = ScriptProgress.objects.get(script__slug='edtrac_smc_monthly', connection=self.connection)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_smc_monthly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).__unicode__(), 'Not Started')
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time.hour, 10)
        seconds_to_nextprog = self.total_seconds(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time - datetime.datetime.now())
        seconds_to_monthday = self.total_seconds(_date_of_monthday(5) - datetime.datetime.now())
        self.assertEquals(seconds_to_nextprog, seconds_to_monthday)

    def testMonthlyGEMPolls(self):
        self.register_reporter('4')
        Script.objects.filter(slug__in=['edtrac_gem_monthly']).update(enabled=True)
        prog = ScriptProgress.objects.get(script__slug='edtrac_gem_monthly', connection=self.connection)
        d = _date_of_monthday(20)
        seconds_to_20th = self.total_seconds(d - datetime.datetime.now())
        self.elapseTime2(prog, seconds_to_20th+(1*60*60)) #seconds to 20th day + one hour
        prog = ScriptProgress.objects.get(script__slug='edtrac_gem_monthly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_gem_monthly').steps.get(order=0).poll.question)
        self.fake_incoming('St Peters PS, St John PS')
        self.assertEquals(Script.objects.get(slug='edtrac_gem_monthly').steps.get(order=0).poll.responses.all().order_by('-date')[0].eav.poll_text_value, 'St Peters PS, St John PS')
        self.elapseTime2(prog, 1)
        prog = ScriptProgress.objects.get(script__slug='edtrac_gem_monthly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_gem_monthly').steps.get(order=1).poll.question)
        self.fake_incoming('St Peters PS, St John PS')
        self.assertEquals(Script.objects.get(slug='edtrac_gem_monthly').steps.get(order=1).poll.responses.all().order_by('-date')[0].eav.poll_text_value, 'St Peters PS, St John PS')
        self.elapseTime2(prog, 1)
        prog = ScriptProgress.objects.get(script__slug='edtrac_gem_monthly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_gem_monthly').steps.get(order=2).poll.question)
        self.fake_incoming('50')
        self.assertEquals(Script.objects.get(slug='edtrac_gem_monthly').steps.get(order=2).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 50)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_gem_monthly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).__unicode__(), 'Not Started')
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time.hour, 10)
        seconds_to_nextprog = self.total_seconds(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time - datetime.datetime.now())
        seconds_to_monthday = self.total_seconds(_date_of_monthday(20) - datetime.datetime.now())
        self.assertEquals(seconds_to_nextprog, seconds_to_monthday)


    def testTermlyHeadTeacherPolls(self):
        self.register_reporter('head teacher')
        Script.objects.filter(slug__in=['edtrac_head_teachers_weekly', 'edtrac_head_teachers_monthly', 'edtrac_head_teachers_termly']).update(enabled=True)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_termly', connection=self.connection)
        d = _next_term_question_date()
        seconds_to_midterm = self.total_seconds(d - datetime.datetime.now())
        self.elapseTime2(prog, seconds_to_midterm+(1*60*60)) #seconds to 25th + one hour
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_termly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=0).poll.question)
        self.fake_incoming('85')
        self.assertEquals(Message.objects.filter(direction='I').order_by('-date')[0].application, 'script')
        print Message.objects.all()
        self.assertEquals(Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=0).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 85)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_termly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=1).poll.question)
        self.fake_incoming('25')
        self.assertEquals(Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=1).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 25)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_termly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=2).poll.question)
        self.fake_incoming('25')
        self.assertEquals(Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=2).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 25)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_termly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=3).poll.question)
        self.fake_incoming('25')
        self.assertEquals(Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=3).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 25)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_termly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=4).poll.question)
        self.fake_incoming('25')
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_termly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=5).poll.question)
        self.fake_incoming('25')
        self.assertEquals(Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=5).poll.responses.all().order_by('-date')[0].eav.poll_number_value, 25)
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_termly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=6).poll.question)
        self.fake_incoming('yes')
        self.assertEquals(Script.objects.get(slug='edtrac_head_teachers_termly').steps.get(order=6).poll.responses.all().order_by('-date')[0].eav.poll_text_value, 'yes')
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_head_teachers_termly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).__unicode__(), 'Not Started')
        #time checks
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time.date(), d.date())
        # micro seconds make test fail
        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time.time().hour, d.time().hour)
    #        self.assertEquals(ScriptProgress.objects.get(connection=self.connection, script=prog.script).time.time().minute, d.time().minute)
    
    def testPollRetryRules(self):
        self.register_reporter('1')
        Script.objects.filter(slug__in=['edtrac_teachers_weekly', 'edtrac_teachers_monthly']).update(enabled=True)
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        seconds_to_thursday = self.total_seconds(_next_thursday() - datetime.datetime.now())
        self.elapseTime2(prog, seconds_to_thursday+(1*60*60)) #seconds to thursday + one hour
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        check_progress(prog.script)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=0).poll.question)
        check_progress(prog.script)
        #script should remain on the same step
        self.assertEquals(ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly').step.order, 0)
        #no double questioning
        self.assertEquals(Message.objects.filter(direction='O', text=Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=0).poll.question).count(), 1)
        #if time < retry_offset
        self.elapseTime2(prog, 61)
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        check_progress(prog.script)
        #script should remain on the same step
        self.assertEquals(ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly').step.order, 0)
        #no double questioning
        self.assertEquals(Message.objects.filter(direction='O', text=Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=0).poll.question).count(), 1)
        #if time < retry_offset
        self.elapseTime2(prog, (86400 - 60))
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        check_progress(prog.script)
        #script should remain on the same step
        self.assertEquals(ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly').step.order, 0)
        #no double questioning
        self.assertEquals(Message.objects.filter(direction='O', text=Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=0).poll.question).count(), 1)
        #elapse retry_offset ===> another 3 seconds subtructed from scriptprogress.time
        self.elapseTime2(prog, 3)
        prog = ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly', connection=self.connection)
        check_progress(prog.script)
        #script should remain on the same step
        self.assertEquals(ScriptProgress.objects.get(script__slug='edtrac_teachers_weekly').step.order, 0)
        #the question should be resent out!
        self.assertEquals(Message.objects.filter(direction='O', text=Script.objects.get(slug='edtrac_teachers_weekly').steps.get(order=0).poll.question).count(), 2)
        self.fake_incoming('40')


    def testRescheduleWeeklyPolls(self):
        ScriptProgress.objects.all().delete()
        self.register_reporter('1', '8675349')
        self.register_reporter('2', '8675319')
        self.register_reporter('3', '8675329')
        weekly_scripts = Script.objects.filter(slug__endswith='_weekly')
        Script.objects.filter(slug__in=weekly_scripts.values_list('slug', flat=True)).update(enabled=True)
        for sp in ScriptProgress.objects.filter(script__slug__in=weekly_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        self.assertEquals(ScriptProgress.objects.filter(script__slug__in=weekly_scripts.values_list('slug', flat=True))[0].time.year, datetime.datetime.now().year - 1)
        reschedule_weekly_polls('teachers')
        next_thursday = _next_thursday()
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675349', script__slug='edtrac_teachers_weekly').time, next_thursday)
        reschedule_weekly_polls('head teachers')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_weekly').time, next_thursday)
        reschedule_weekly_polls('smc')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675329', script__slug='edtrac_smc_weekly').time, next_thursday)
        for sp in ScriptProgress.objects.filter(script__slug__in=weekly_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        #        reschedule_weekly_polls('gem')
        #        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675339', script__slug='edtrac_gem_weekly').time.date(), next_thursday.date())
        reschedule_weekly_polls()
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675349', script__slug='edtrac_teachers_weekly').time, next_thursday)
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_weekly').time, next_thursday)
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675329', script__slug='edtrac_smc_weekly').time, next_thursday)

    def testRescheduleMonthlyPolls(self):
        ScriptProgress.objects.all().delete()
        self.register_reporter('1', '8675349')
        self.register_reporter('2', '8675319')
        self.register_reporter('3', '8675329')
        self.register_reporter('4', '8675339')
        monthly_scripts = Script.objects.filter(slug__endswith='_monthly')
        Script.objects.filter(slug__in=monthly_scripts.values_list('slug', flat=True)).update(enabled=True)
        for sp in ScriptProgress.objects.filter(script__slug__in=monthly_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        self.assertEquals(ScriptProgress.objects.filter(script__slug__in=monthly_scripts.values_list('slug', flat=True))[0].time.year, datetime.datetime.now().year - 1)
        reschedule_monthly_polls('head teachers')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_monthly').time.date(), _date_of_monthday('last').date())
        reschedule_monthly_polls('smc')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675329', script__slug='edtrac_smc_monthly').time.date(), _date_of_monthday(5).date())
        reschedule_monthly_polls('gem')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675339', script__slug='edtrac_gem_monthly').time.date(), _date_of_monthday(20).date())
        for sp in ScriptProgress.objects.filter(script__slug__in=monthly_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        reschedule_monthly_polls()
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_monthly').time.date(), _date_of_monthday('last').date())
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675329', script__slug='edtrac_smc_monthly').time.date(), _date_of_monthday(5).date())
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675339', script__slug='edtrac_gem_monthly').time.date(), _date_of_monthday(20).date())

    def testRescheduleTermlyPolls(self):
        ScriptProgress.objects.all().delete()
        self.register_reporter('1', '8675349')
        self.register_reporter('2', '8675319')
        self.register_reporter('3', '8675329')
        self.register_reporter('4', '8675339')
        termly_scripts = Script.objects.filter(slug__endswith='_termly')
        Script.objects.filter(slug__in=termly_scripts.values_list('slug', flat=True)).update(enabled=True)
        for sp in ScriptProgress.objects.filter(script__slug__in=termly_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        reschedule_termly_polls('head teachers')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_termly').time.date(), _next_term_question_date().date())
        reschedule_termly_polls('smc')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675329', script__slug='edtrac_smc_termly').time.date(), _next_term_question_date(rght=True).date())
        for sp in ScriptProgress.objects.filter(script__slug__in=termly_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        reschedule_termly_polls()
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_termly').time.date(), _next_term_question_date().date())
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675329', script__slug='edtrac_smc_termly').time.date(), _next_term_question_date(rght=True).date())
        for sp in ScriptProgress.objects.filter(script__slug__in=termly_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        reschedule_termly_polls('smc', date='2012-4-16')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675329', script__slug='edtrac_smc_termly').time.date(), datetime.datetime(2012, 4, 16).date())
        for sp in ScriptProgress.objects.filter(script__slug__in=termly_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        reschedule_termly_polls('all', '2012-4-17')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_termly').time.date(), datetime.datetime(2012, 4, 17).date())
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675329', script__slug='edtrac_smc_termly').time.date(), datetime.datetime(2012, 4, 17).date())
        
    def testRescheduleMidTermPolls(self):
        ScriptProgress.objects.all().delete()
        self.register_reporter('1', '8675349')
        self.register_reporter('2', '8675319')
        self.register_reporter('3', '8675329')
        self.register_reporter('4', '8675339')
        midterm_scripts = Script.objects.filter(slug__endswith='_midterm')
        Script.objects.filter(slug__in=midterm_scripts.values_list('slug', flat=True)).update(enabled=True)
        for sp in ScriptProgress.objects.filter(script__slug__in=midterm_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        reschedule_midterm_polls('head teachers')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_midterm').time.date(), _next_midterm().date())
        for sp in ScriptProgress.objects.filter(script__slug__in=midterm_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        reschedule_midterm_polls()
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_midterm').time.date(), _next_midterm().date())
        for sp in ScriptProgress.objects.filter(script__slug__in=midterm_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        reschedule_midterm_polls('head teachers', date='2012-10-08')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_midterm').time.date(), datetime.datetime(2012, 10, 8).date())
        for sp in ScriptProgress.objects.filter(script__slug__in=midterm_scripts.values_list('slug', flat=True)):
            self.elapseTime2(sp, 13*31*24*60*60)
        reschedule_termly_polls('all', '2012-10-08')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_midterm').time.date(), datetime.datetime(2012, 10, 8).date())
        
    def testRescheduleMidTermManagementCommand(self):
        ScriptProgress.objects.all().delete()
        self.register_reporter('1', '8675349')
        self.register_reporter('2', '8675319')
        self.register_reporter('3', '8675329')
        self.register_reporter('4', '8675339')
        call_command('reschedule_midterm_polls', group='Head Teachers', date='2012-10-08')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_midterm').time.date(), datetime.datetime(2012, 10, 8).date())
        
    def testRescheduleTermlyManagementCommand(self):
        ScriptProgress.objects.all().delete()
        self.register_reporter('1', '8675349')
        self.register_reporter('2', '8675319')
        self.register_reporter('3', '8675329')
        self.register_reporter('4', '8675339')
        call_command('reschedule_termly_polls', group=['Head Teachers', 'SMC'], date='2012-4-17')
        self.assertEquals(ScriptProgress.objects.get(connection__identity='8675319', script__slug='edtrac_head_teachers_termly').time.date(), datetime.datetime(2012, 4, 17).date())
        
    
#def load_edtrac_data():
##    User.objects.get_or_create(username='admin')
#    call_command('loaddata', 'edtrac_data')
#    
#
#post_syncdb.connect(load_edtrac_data, weak=True)