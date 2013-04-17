# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import datetime
import dateutils
from django.test import TestCase
from rapidsms_xforms.models import *
from rapidsms.contrib.locations.models import Location, LocationType
from rapidsms.models import Connection, Backend
from script.utils.outgoing import check_progress
from script.models import Script, ScriptProgress, ScriptStep,ScriptSession
from rapidsms_httprouter.router import get_router
from education.models import EmisReporter, School,reschedule_monthly_script
from django.test.client import Client
from education.test.utils import *
from poll.models import Poll

class TestCurriculumProgressView(TestCase):
    def setUp(self):
        settings.FIRST_TERM_BEGINS = dateutils.increment(datetime.datetime.now(),weeks=-16)
        settings.SECOND_TERM_BEGINS = dateutils.increment(datetime.datetime.now(),weeks=-4)
        settings.THIRD_TERM_BEGINS =  dateutils.increment(datetime.datetime.now(),weeks=8)

        settings.SCHOOL_TERM_START = settings.SECOND_TERM_BEGINS
        self.poll_response_current_week_date = dateutils.increment(datetime.datetime.now(), weeks=-1,days=3)
        self.poll_response_previous_week_date = dateutils.increment(datetime.datetime.now(), weeks=-4,days=3)

        ht = Group.objects.create(name='Head Teachers')
        country = LocationType.objects.create(name='country', slug='country')
        district = LocationType.objects.create(name='district', slug='district')
        uganda_fields = dict(rght=15274, name="Uganda", level=0, tree_id=1, lft=1, type=country)

        self.root_node = Location.objects.create(**uganda_fields)
        self.admin_user = create_user_with_group("John", Role.objects.create(name="Admins"), self.root_node)
        self.user = User.objects.create(username="Bosco", password="Bosco")

        kampala_point_fields = dict(latitude="0.3162800000", longitude="32.5821900000")
        kampala_point = Point.objects.create(**kampala_point_fields)
        kampala_fields = dict(rght=10901, tree_parent=self.root_node, name="Kampala", point=kampala_point, level=1,
                              tree_id=1, lft=10686, type=district)
        self.kampala_district = Location.objects.create(**kampala_fields)

        gulu_point_fields = dict(latitude="2.7666700000", longitude="32.3055600000")
        gulu_point = Point.objects.create(**gulu_point_fields)
        gulu_fields = dict(rght=9063, tree_parent=self.root_node, name="Gulu", point=gulu_point, level=1, tree_id=1,
                           lft=8888, type=district)
        self.gulu_district = Location.objects.create(**gulu_fields)

        self.school = School.objects.create(name="Don Bosco School", location=self.root_node)
        self.school1 = School.objects.create(name="St. Mary School", location=self.root_node)

        self.emisreporter1 = EmisReporter.objects.create(name="Reporter1", reporting_location=self.kampala_district)
        self.emisreporter1.schools.add(self.school)
        self.emisreporter1.grade=u'P3'
        self.emisreporter1.groups.add(ht)
        self.emisreporter1.save()

        self.emisreporter2 = EmisReporter.objects.create(name="Reporter2", reporting_location=self.kampala_district)
        self.emisreporter2.schools.add(self.school1)
        self.emisreporter2.grade=u'P3'
        self.emisreporter2.groups.add(ht)
        self.emisreporter2.save()

        self.emisreporter3 = EmisReporter.objects.create(name="Reporter3", reporting_location=self.gulu_district)
        self.emisreporter3.schools.add(self.school)
        self.emisreporter3.grade=u'P3'
        self.emisreporter3.groups.add(ht)
        self.emisreporter3.save()

        self.backend = Backend.objects.create(name='fake_backed')
        self.connection1 = Connection.objects.create(identity="02022222220", backend=self.backend,
                                                     contact=self.emisreporter1)
        self.connection2 = Connection.objects.create(identity="02022222221", backend=self.backend,
                                                     contact=self.emisreporter2)
        self.connection3 = Connection.objects.create(identity="02022222222", backend=self.backend,
                                                     contact=self.emisreporter3)
        create_attribute()
        self.poll, self.poll_created = Poll.objects.get_or_create(name='edtrac_p3curriculum_progress', user=self.user, type=Poll.TYPE_NUMERIC, question='What sub theme number of the P3 Literacy curriculum are you teaching this week?', default_response='')
        self.script = Script.objects.create(slug="edtrac_p3_teachers_weekly", name = "Revised P3 Teachers Weekly Script", enabled = False)
        self.script.steps.add(ScriptStep.objects.get_or_create(
            script=self.script,
            poll=self.poll,
            order=0,
            rule=ScriptStep.WAIT_MOVEON,
            num_tries=1,
            start_offset=0,
            retry_offset=86400,
            giveup_offset=86400,
            )[0])

    def test_curriculum_progress_view_for_current_week(self):
        reschedule_monthly_script('Head Teachers',datetime.datetime.now().strftime("%Y-%m-%d"),'edtrac_p3_teachers_weekly')
        check_progress(self.script)
        self.fake_incoming_with_date('5.3',self.connection1,self.poll_response_current_week_date)
        self.fake_incoming_with_date('5.3',self.connection2,self.poll_response_current_week_date)
        self.fake_incoming_with_date('5.2',self.connection3,self.poll_response_current_week_date)
        client=Client()
        client.login(username='John',password='password')
        response=client.get('/edtrac/dash-admin-progress/')
        self.assertEqual(6.1,response.context['target'])
        self.assertEqual(5.3,response.context['current_mode'][0][0])

    def test_curriculum_progress_view_for_specified_week(self):
        specified_week=dateutils.increment(datetime.datetime.now().date(),weeks=-4,days=1).strftime("%Y-%m-%d")
        reschedule_monthly_script('Head Teachers',specified_week,'edtrac_p3_teachers_weekly')
        check_progress(self.script)
        self.fake_incoming_with_date('5.1',self.connection1,self.poll_response_previous_week_date)
        self.fake_incoming_with_date('5.1',self.connection2,self.poll_response_previous_week_date)
        self.fake_incoming_with_date('5.1',self.connection3,self.poll_response_previous_week_date)
        client=Client()
        client.login(username='John',password='password')
        week_start=dateutils.increment(datetime.datetime.now().date(),weeks=-4,days=1).strftime("%d,%b,%Y")
        week_end=dateutils.increment(datetime.datetime.now().date(),weeks=-3).strftime("%d,%b,%Y")
        week_choices=week_start+" to "+week_end
        response=client.post('/edtrac/dash-admin-progress/',{'choose_week_to_view':week_choices})
        self.assertEqual(5.1,response.context['target'])
        self.assertEqual(5.1,response.context['current_mode'][0][0])

    def test_mode_by_district(self):
        reschedule_monthly_script('Head Teachers',datetime.datetime.now().strftime("%Y-%m-%d"),'edtrac_p3_teachers_weekly')
        check_progress(self.script)
        self.fake_incoming_with_date('5.3',self.connection1,self.poll_response_current_week_date)
        self.fake_incoming_with_date('5.3',self.connection2,self.poll_response_current_week_date)
        self.fake_incoming_with_date('5.2',self.connection3,self.poll_response_current_week_date)
        client=Client()
        client.login(username='John',password='password')
        response=client.get('/edtrac/dash-admin-progress/')
        self.assertTrue(5.3 in dict(response.context['location_data'][self.kampala_district]))
        self.assertEqual('Progress undetermined this week',response.context['location_data'][self.gulu_district])

    def fake_incoming_with_date(self, message, connection, date):
        router = get_router()
        handled = router.handle_incoming(connection.backend.name, connection.identity, message)
        for response in handled.poll_responses.all():
            response.date = date
            response.save()

    def tearDown(self):
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        School.objects.all().delete()
        EmisReporter.objects.all().delete()
        Connection.objects.all().delete()
        Backend.objects.all().delete()
        Poll.objects.all().delete()
        User.objects.all().delete()
        Group.objects.all().delete()
        Attribute.objects.all().delete()
        Script.objects.all().delete()
        ScriptProgress.objects.all().delete()
        ScriptStep.objects.all().delete()
        ScriptSession.objects.all().delete()

