"""
Basic tests for CVS
"""

from django.test import TestCase
from django.contrib.auth.models import User, Group
from rapidsms.messages.incoming import IncomingMessage
from rapidsms_xforms.models import *
from rapidsms_httprouter.models import Message
from rapidsms.contrib.locations.models import Location, LocationType
import datetime
from rapidsms.models import Connection, Backend, Contact
from rapidsms.messages.incoming import IncomingMessage
from rapidsms_xforms.models import XForm, XFormSubmission
from django.conf import settings
from script.utils.outgoing import check_progress
from script.models import Script, ScriptProgress, ScriptSession, ScriptResponse
from education.management import *
from rapidsms_httprouter.router import get_router
from script.signals import script_progress_was_completed, script_progress
from poll.management import create_attributes
from .models import EmisReporter, School
from django.db import connection
from script.utils.outgoing import check_progress
from django.core.management import call_command
from unregister.models import Blacklist


class ModelTest(TestCase): #pragma: no cover
    
    def fake_incoming(self, message, connection=None):
        if connection is None:
            connection = self.connection
        router = get_router()
        router.handle_incoming(connection.backend.name, connection.identity, message)
        form = XForm.find_form(message)
        if form:
            return XFormSubmission.objects.all().order_by('-created')[0]


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


    def setUp(self):
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            site_id = getattr(settings, 'SITE_ID', 1)
            Site.objects.get_or_create(pk=site_id, defaults={'domain':'rapidemis.com'})
#        fixtures = ['initial_data.json']
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


    def fake_script_dialog(self, script_prog, connection, responses, emit_signal=True):
        script = script_prog.script
        ss = ScriptSession.objects.create(script=script, connection=connection, start_time=datetime.datetime.now())
        for poll_name, resp in responses:
            poll = script.steps.get(poll__name=poll_name).poll
            poll.process_response(self.spoof_incoming_obj(resp))
            resp = poll.responses.all()[0]
            ScriptResponse.objects.create(session=ss, response=resp)
        if emit_signal:
            script_progress_was_completed.send(connection=connection, sender=script_prog)
        return ss

    def testBasicAutoReg(self):
        self.fake_incoming('join')
        self.assertEquals(ScriptProgress.objects.count(), 1)
        script_prog = ScriptProgress.objects.all()[0]
        self.assertEquals(script_prog.script.slug, 'emis_autoreg')

        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_role', 'teacher'), \
            ('emis_class', 'P3'),\
            ('emis_district', 'kampala'), \
            ('emis_subcounty', 'kampala'), \
            ('emis_school', 'st. marys'), \
            ('emis_name', 'testy mctesterton'), \
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.kampala_subcounty)
        self.assertEquals(contact.schools.all()[0], self.kampala_school)
        self.assertEquals(contact.groups.all()[0].name, 'Teachers')
        self.assertEquals(contact.grade, 'P3')
        self.assertEquals(contact.default_connection, self.connection)

    def testBadAutoReg(self):
        """
        Crummy answers
        """
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_role', 'bodaboda'), \
            ('emis_district', 'kampala'), \
            ('emis_subcounty', 'amudat'), \
            ('emis_name', 'bad tester'), \
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.groups.all()[0].name, 'Other EMIS Reporters')
        self.assertEquals(contact.reporting_location, self.kampala_district)

    def testAutoRegNoLocationData(self):

        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_role', 'teacher'), \
            ('emis_name', 'no location data tester'), \
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.reporting_location, self.root_node)

    def testAutoRegNoRoleNoName(self):
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_district', 'kampala'), \
            ('emis_subcounty', 'Gul'), \
            ('emis_one_school', 'St Marys'), \
        ])
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.groups.all()[0].name, 'Other EMIS Reporters')
        self.assertEquals(contact.reporting_location, self.gulu_subcounty)
        self.assertEquals(contact.name, 'Anonymous User')

    def testGemAutoReg(self):
        self.fake_incoming('join')
        self.assertEquals(ScriptProgress.objects.count(), 1)
        script_prog = ScriptProgress.objects.all()[0]
        self.assertEquals(script_prog.script.slug, 'emis_autoreg')

        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_role', 'gem'), \
            ('emis_district', 'kampala'), \
            ('emis_many_school', 'st. marys, st. peters'), \
            ('emis_name', 'testy mctesterton'), \
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.kampala_district)
        self.assertEquals(contact.schools.count(), 2)
        self.assertEquals(len(set(contact.schools.all()) & set([self.kampala_school2, self.kampala_school3])), 2)
        self.assertEquals(contact.groups.all()[0].name, 'GEM')

    def testGemQuestions(self):
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.get(connection=self.connection)
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=0, l=20)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, 'Welcome to the SMS based school data collection pilot.The information you provide is valuable to improving the quality of education in Uganda.')
        script_prog = ScriptProgress.objects.get(connection=self.connection)
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=0, l=20)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, 'To register,tell us your role? Teacher, Head Teacher, SMC, GEM, CCT, DEO,or District Official.Reply with one of the roles listed.')
        self.fake_incoming('GEM')
        script_prog = ScriptProgress.objects.get(connection=self.connection)
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=0, l=20)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, 'What is the name of your district?')
        self.fake_incoming('Kampala')
        script_prog = ScriptProgress.objects.get(connection=self.connection)
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=0, l=20)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, 'Name the schools you are resonsible for.Separate each school name with a comma, for example "St. Mary Secondary,Pader Primary"')
        self.fake_incoming('St. Marys, St. Peters')
        script_prog = ScriptProgress.objects.get(connection=self.connection)
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=0, l=20)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, 'What is your name?')
        self.fake_incoming('test mctester')
        script_prog = ScriptProgress.objects.get(connection=self.connection)
        self.elapseTime2(script_prog, 3601)
        call_command('check_script_progress', e=0, l=20)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, 'Welcome to the school monitoring pilot.The information you provide contributes to keeping children in school.')

    def testDoubleReg(self):
        self.fake_incoming('join')
        self.assertEquals(ScriptProgress.objects.count(), 1)
        script_prog = ScriptProgress.objects.all()[0]
        self.assertEquals(script_prog.script.slug, 'emis_autoreg')

        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_role', 'teacher'), \
            ('emis_district', 'kampala'), \
            ('emis_subcounty', 'kampala'), \
            ('emis_one_school', 'st. marys'), \
            ('emis_name', 'testy mctesterton'), \
        ])

        self.assertEquals(EmisReporter.objects.count(), 1)
        contact = EmisReporter.objects.all()[0]
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.kampala_subcounty)
        self.assertEquals(contact.schools.all()[0], self.kampala_school)
        self.assertEquals(contact.groups.all()[0].name, 'Teachers')

        self.fake_incoming('join')
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, "You are already in the system and do not need to 'Join' again.")
        self.assertEquals(ScriptProgress.objects.filter(script__slug='emis_autoreg').count(), 1)

    def testQuitRejoin(self):
        #first join
        self.fake_incoming('join')
        self.assertEquals(ScriptProgress.objects.count(), 1)
        script_prog = ScriptProgress.objects.all()[0]
        self.assertEquals(script_prog.script.slug, 'emis_autoreg')

        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_role', 'teacher'), \
            ('emis_district', 'kampala'), \
            ('emis_subcounty', 'kampala'), \
            ('emis_one_school', 'st. marys'), \
            ('emis_name', 'testy mctesterton'), \
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)

        #then quit
        self.fake_incoming('quit')
        self.assertEquals(Blacklist.objects.all()[0].connection, self.connection)
        self.assertEquals(EmisReporter.objects.all()[0].active, False)

        #rejoin
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]

        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_role', 'teacher'), \
            ('emis_district', 'kampala'), \
            ('emis_subcounty', 'kampala'), \
            ('emis_one_school', 'st. marys'), \
            ('emis_name', 'testy mctesterton'), \
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)

    def assertScriptSkips(self, connection, role, initial_question, final_question):
        connection = Connection.objects.create(identity=connection, backend=self.backend)
        script = Script.objects.get(slug='emis_autoreg')
        script_prog = ScriptProgress.objects.create(script=script, connection=connection, step=script.steps.get(poll__name=initial_question), status='C', num_tries=1)
        script_prog.set_time(datetime.datetime.now() - datetime.timedelta(1))
        self.fake_script_dialog(script_prog, connection, [\
            ('emis_role', role)
        ], emit_signal=False)
        check_progress(connection)
        script_prog = ScriptProgress.objects.get(connection=connection)
        self.assertEquals(script_prog.step.poll.name, final_question)


    def testAutoRegTransitions(self):
        self.assertScriptSkips('8675310', 'deo', 'emis_district', 'emis_name')
        self.assertScriptSkips('8675311', 'cct', 'emis_district', 'emis_name')
        self.assertScriptSkips('8675312', 'district officials', 'emis_district', 'emis_name')

        self.assertScriptSkips('8675313', 'gem', 'emis_district', 'emis_subcounty')
#        self.assertScriptSkips('8675313', 'gem', 'emis_district', 'emis_name')
        self.assertScriptSkips('8675314', 'smc', 'emis_district', 'emis_subcounty')
        self.assertScriptSkips('8675315', 'head teachers', 'emis_district', 'emis_subcounty')
        self.assertScriptSkips('8675316', 'teachers', 'emis_district', 'emis_subcounty')

        self.assertScriptSkips('8675317', 'gem', 'emis_subcounty', 'emis_many_school')

        self.assertScriptSkips('8675318', 'teachers', 'emis_subcounty', 'emis_one_school')
        self.assertScriptSkips('8675319', 'head teachers', 'emis_subcounty', 'emis_one_school')
        self.assertScriptSkips('8675320', 'smc', 'emis_subcounty', 'emis_one_school')


    def assertXFormAdvancedScript(self, message, completed_step, advance=True):
        self.fake_incoming(message)
        script_prog = ScriptProgress.objects.all()[0]
        self.assertEquals(script_prog.step.order, completed_step)
        self.assertEquals(script_prog.status, 'C')
        # advance to next step
        if advance:
            script_prog.step = script_prog.script.steps.get(order=completed_step + 1)
            script_prog.status = 'P'
            script_prog.save()

    def testOtherScriptHandlers(self):
        # fake that this connection has already gone through autoreg
        contact = Contact.objects.create(name='Testy McTesterton')
        self.connection.contact = contact
        self.connection.save()

        script = Script.objects.get(slug='emis_annual')
        script_prog = ScriptProgress.objects.create(script=script, connection=self.connection, step=script.steps.get(order=0), status='P')

        self.assertXFormAdvancedScript('classrooms 2 2 3 3 4 4 5', 0)
        self.assertXFormAdvancedScript('classroomsused 2 2 3 3 4 4 5', 1)
        self.assertXFormAdvancedScript('latrines g 20 b 26 f 7 m 9', 2)
        self.assertXFormAdvancedScript('latrinesused g 20 b 26 f 7 m 9', 3)
        self.assertXFormAdvancedScript('deploy f 2 m 4', 4)
        self.assertXFormAdvancedScript('enrolledb 200 200 30 45 89 90 23', 5)
        self.assertXFormAdvancedScript('enrolledg 300 120 80 67 43 12 5', 6, False)

    def testBasicSubmission(self):
        self.fake_incoming('gemabuse 20 school St Mary')
        self.assertEquals(XFormSubmission.objects.count(), 1)

    def testGemAbuse(self):
        s = self.fake_incoming('gemabuse 20 school St Mary')
        self.assertEquals(s.eav.gemabuse_cases, 20)
        self.assertEquals(s.eav.gemabuse_school, 'St Mary')
        self.assertEquals(Message.objects.all().order_by('-date')[0].text, "Thank you. Your data on gemabuse has been received")

    def testAttendanceFeedback(self):
        s = self.fake_incoming('boys 20, 30, 24, 11, 39, 61, 34')
        self.assertEquals(s.eav.boys_p2, 30)
        self.assertEquals(Message.objects.all().order_by('-date')[0].text, "Thank you. Your data on boys has been received")
        week = 7 * 86400
        self.elapseTime(XFormSubmission.objects.all().order_by('-created')[0], week)
        s = self.fake_incoming('boys 25, 29, 27, 30, 15, 61, 34')
        self.assertEquals(s.eav.boys_p2, 29)
        perc = (float(sum([20, 30, 24, 11, 39, 61, 34])) / float(sum([25, 29, 27, 30, 15, 61, 34]))) * 100
        self.assertEquals(Message.objects.all().order_by('-date')[0].text, "Thank you. Attendance for boys is %.1f percent higher than it was last week" % (100.0 - perc))

    def testTeacherAttendance(self):
        s = self.fake_incoming('teachers f 20, m 11')
        self.assertEquals(Message.objects.all().order_by('-date')[0].text, "Thank you. Your data on teachers has been received")
        week = 7 * 86400
        self.elapseTime(XFormSubmission.objects.all().order_by('-created')[0], week)
        s = self.fake_incoming('teachers f 5, m 10')
        perc = (float(sum([5, 10])) / float(sum([20, 11]))) * 100
        self.assertEquals(Message.objects.all().order_by('-date')[0].text, "Thank you. Attendance for teachers is %.1f percent lower than it was last week" % (100.0 - perc))

    def testScriptReschedule(self):
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]

        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_role', 'teacher'), \
            ('emis_district', 'kampala'), \
            ('emis_subcounty', 'kampala'), \
            ('emis_one_school', 'st. marys'), \
            ('emis_name', 'testy mctesterton'), \
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)
        ScriptProgress.objects.exclude(script__slug='emis_abuse').delete()
        prog = ScriptProgress.objects.get(script__slug='emis_abuse')
        self.elapseTime2(prog, 50 * 86400)
        call_command('check_script_progress', e=0, l=20)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='emis_abuse').steps.all()[0].poll.question)
        prog = ScriptProgress.objects.get(script__slug='emis_abuse')
        self.elapseTime2(prog, 86400)
        call_command('check_script_progress', e=0, l=20)
        self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='emis_abuse').steps.all()[0].poll.question)
        prog = ScriptProgress.objects.get(script__slug='emis_abuse')
        self.elapseTime2(prog, 2 * 86400)
        call_command('check_script_progress', e=0, l=20)
        self.assertEquals(Message.objects.filter(text='How many abuse cases were recorded in the record book this month?').count(), 2)
        prog = ScriptProgress.objects.get(script__slug='emis_abuse')
        self.elapseTime2(prog, 31 * 86400)
        call_command('check_script_progress', e=0, l=20)
        self.assertEquals(Message.objects.filter(text='How many abuse cases were recorded in the record book this month?').count(), 3)

    def testAnnualScriptReschedule(self):
        #TO DO: add setting for schedule of annual scripts
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]

        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_role', 'teacher'), \
            ('emis_district', 'kampala'), \
            ('emis_subcounty', 'kampala'), \
            ('emis_one_school', 'st. marys'), \
            ('emis_name', 'testy mctesterton'), \
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)
        ScriptProgress.objects.exclude(script__slug='emis_annual').delete()
        prog = ScriptProgress.objects.get(script__slug='emis_annual')

        #nothing going out after three weeks
        self.elapseTime2(prog, 21 * 86400)
        prog = ScriptProgress.objects.get(script__slug='emis_annual')
        call_command('check_script_progress', e=0, l=20)
        if Message.objects.filter(direction="O").count():
            self.assertNotEqual(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='emis_annual').steps.all()[0].poll.question)

        #12 weeks after beginning of each year, annual messages are sent out
        d = datetime.datetime.now()
        start_of_year = datetime.datetime(d.year, 1, 1, d.hour, d.minute, d.second, d.microsecond)\
         if d.month < 3 else datetime.datetime(d.year + 1, 1, 1, d.hour, d.minute, d.second, d.microsecond)
        script_start = start_of_year + datetime.timedelta(weeks=(getattr(settings, 'SCHOOL_ANNUAL_MESSAGES_START', 12) + 3))
        import time
        self.elapseTime2(prog, time.mktime(script_start.timetuple()))
        for x in range(Script.objects.get(slug='emis_annual').steps.count()):
            prog = ScriptProgress.objects.get(script__slug='emis_annual')
            self.elapseTime2(prog, 61)
            for y in range(2):
                call_command('check_script_progress', e=0, l=20)
                self.assertEquals(Message.objects.filter(direction='O').order_by('-date')[0].text, Script.objects.get(slug='emis_annual').steps.all()[x].poll.question)
                self.elapseTime2(prog, 86400)
                if y == 1:
                    #Factor in giveup_offset=86400
                    self.elapseTime2(prog, 86400)
                    call_command('check_script_progress', e=0, l=20)
        #emis_annual script marked as ended for this session
        self.assertEquals(ScriptSession.objects.filter(script__slug='emis_annual', end_time=None).count(), 0)

        #annual script for this user re-scheduled to 12 weeks after beginning of next year
        d = ScriptSession.objects.filter(script__slug='emis_annual', connection=self.connection).order_by('-end_time')[0].end_time
        start_of_year = datetime.datetime(d.year + 1, 1, 1, d.hour, d.minute, d.second, d.microsecond)
        script_start = start_of_year + datetime.timedelta(weeks=getattr(settings, 'SCHOOL_ANNUAL_MESSAGES_START', 12))
        self.assertEquals(ScriptProgress.objects.get(script__slug='emis_annual', connection=self.connection).time, script_start)

    def testTermlyScriptReschedule(self):
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]

        self.fake_script_dialog(script_prog, self.connection, [\
            ('emis_role', 'SMC'), \
            ('emis_district', 'kampala'), \
            ('emis_subcounty', 'kampala'), \
            ('emis_one_school', 'st. marys'), \
            ('emis_name', 'testy mctesterton'), \
        ])
        self.assertEquals(EmisReporter.objects.count(), 1)

        prog = ScriptProgress.objects.get(script__slug='emis_smc_termly')
        self.assertEqual(prog.time.month, 4, 'Termly smc polls are scheduled to go out on %s'%prog.time)
