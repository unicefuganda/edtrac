# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

import dateutils
from unittest import TestCase
from django.contrib.auth.models import User, Group
from education.models import School, EmisReporter
from education.reports import get_week_date
from education.views import schools_valid, capitation_grants, total_reporters, p3_absent_boys, p6_boys_absent, p3_absent_girls, p6_girls_absent,f_teachers_absent,m_teachers_absent,head_teachers_female,head_teachers_male
from poll.models import Poll,Response
from rapidsms.contrib.locations.models import Location, LocationType, Point
from rapidsms.models import Backend, Connection
from education.test.utils import *
from django.conf import settings
from rapidsms_httprouter.router import get_router
from datetime import datetime

class TestEdtracDashboard(TestCase):
    def setUp(self):
        time = datetime(2012, 05, 8)
        self.get_time = lambda: time
        settings.SCHOOL_TERM_START = dateutils.increment(time, weeks=-2)
        settings.SCHOOL_TERM_END = dateutils.increment(time, weeks=2)

        self.poll_response_current_week_date = dateutils.increment(time, weeks=-1)
        self.poll_response_past_week_date = dateutils.increment(time)

        htg = Group.objects.create(name='Head Teachers')
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
        self.emisreporter1.groups.add(htg)
        self.emisreporter1.gender="F"
        self.emisreporter1.save()

        self.emisreporter2 = EmisReporter.objects.create(name="Reporter2", reporting_location=self.kampala_district)
        self.emisreporter2.schools.add(self.school1)
        self.emisreporter2.groups.add(htg)
        self.emisreporter2.gender="M"
        self.emisreporter2.save()

        self.emisreporter3 = EmisReporter.objects.create(name="Reporter3", reporting_location=self.gulu_district)
        self.emisreporter3.schools.add(self.school)
        self.emisreporter3.groups.add(htg)
        self.emisreporter3.gender="F"
        self.emisreporter3.save()

        self.backend = Backend.objects.create(name='fake_backed')
        self.connection1 = Connection.objects.create(identity="02022222220", backend=self.backend,
                                                     contact=self.emisreporter1)
        self.connection2 = Connection.objects.create(identity="02022222221", backend=self.backend,
                                                     contact=self.emisreporter2)
        self.connection3 = Connection.objects.create(identity="02022222222", backend=self.backend,
                                                     contact=self.emisreporter3)
        create_attribute()

    def start_upe_poll(self):
        self.upe_grant_poll = Poll.objects.create(name='edtrac_upe_grant',
                                                  question="Have you received your UPE grant this term? Answer  YES or NO or I don't know",
                                                  type=Poll.TYPE_TEXT, user=self.user, response_type=Poll.RESPONSE_TYPE_ONE)
        self.upe_grant_poll.contacts.add(self.emisreporter1, self.emisreporter2, self.emisreporter3)
        self.upe_grant_poll.add_yesno_categories()
        self.upe_grant_poll.save()
        self.upe_grant_poll.start()

    def start_p6_boys_enrollment_poll(self):
        self.p6_boys_enrolled_poll = create_poll_with_reporters("edtrac_boysp6_enrollment",
                                                 "How many boys are enrolled in P6 this term?",
                                                 Poll.TYPE_NUMERIC, self.admin_user,
                                                 [self.emisreporter1, self.emisreporter2, self.emisreporter3])
        self.p6_boys_enrolled_poll.save()
        self.p6_boys_enrolled_poll.start()

    def start_p3_boys_enrollment_poll(self):
        self.p3_boys_enrolled_poll = create_poll_with_reporters("edtrac_boysp3_enrollment",
                                                 "How many boys are enrolled in P3 this term?",
                                                 Poll.TYPE_NUMERIC, self.admin_user,
                                                 [self.emisreporter1, self.emisreporter2, self.emisreporter3])
        self.p3_boys_enrolled_poll.save()
        self.p3_boys_enrolled_poll.start()

    def start_p6_girls_enrollment_poll(self):
        self.p6_girls_enrolled_poll = create_poll_with_reporters("edtrac_girlsp6_enrollment",
                                                  "How many girls are enrolled in P6 this term?",
                                                  Poll.TYPE_NUMERIC, self.admin_user,
                                                  [self.emisreporter1, self.emisreporter2, self.emisreporter3])
        self.p6_girls_enrolled_poll.save()
        self.p6_girls_enrolled_poll.start()

    def start_p3_girls_enrollment_poll(self):
        self.p3_girls_enrolled_poll = create_poll_with_reporters("edtrac_girlsp3_enrollment",
                                                  "How many girls are enrolled in P3 this term?",
                                                  Poll.TYPE_NUMERIC, self.admin_user,
                                                  [self.emisreporter1, self.emisreporter2, self.emisreporter3])
        self.p3_girls_enrolled_poll.save()
        self.p3_girls_enrolled_poll.start()

    def start_f_teacher_deployment_poll(self):
        self.f_teacher_deployment_poll=create_poll_with_reporters("edtrac_f_teachers_deployment",
                                                   "How many female teachers are deployed in your school this term?",
                                                   Poll.TYPE_NUMERIC,self.admin_user,
                                                   [self.emisreporter1,self.emisreporter2,self.emisreporter3])
        self.f_teacher_deployment_poll.save()
        self.f_teacher_deployment_poll.start()

    def start_m_teacher_deployment_poll(self):
        self.m_teacher_deployment_poll=create_poll_with_reporters("edtrac_m_teachers_deployment",
                                                   "How many male teachers are deployed in your school this term?",
                                                   Poll.TYPE_NUMERIC,self.admin_user,
                                                   [self.emisreporter1,self.emisreporter2,self.emisreporter3])
        self.m_teacher_deployment_poll.save()
        self.m_teacher_deployment_poll.start()

    def create_emisreporters_of_smc_group(self):
        smc = Group.objects.create(name='SMC')

        self.emisreporter4 = EmisReporter.objects.create(name="Reporter4", reporting_location=self.kampala_district)
        self.emisreporter4.schools.add(self.school)
        self.emisreporter4.groups.add(smc)
        self.emisreporter4.save()

        self.emisreporter5 = EmisReporter.objects.create(name="Reporter5", reporting_location=self.kampala_district)
        self.emisreporter5.schools.add(self.school1)
        self.emisreporter5.groups.add(smc)
        self.emisreporter5.save()

        self.emisreporter6 = EmisReporter.objects.create(name="Reporter6", reporting_location=self.gulu_district)
        self.emisreporter6.schools.add(self.school)
        self.emisreporter6.groups.add(smc)
        self.emisreporter6.save()

        self.connection4 = Connection.objects.create(identity="02022222223", backend=self.backend,
                                                     contact=self.emisreporter4)
        self.connection5 = Connection.objects.create(identity="02022222224", backend=self.backend,
                                                     contact=self.emisreporter5)
        self.connection6 = Connection.objects.create(identity="02022222225", backend=self.backend,
                                                     contact=self.emisreporter6)

    def test_percentage_of_p6_boys_absent(self):
        settings.SCHOOL_HOLIDAYS = []
        self.start_p6_boys_enrollment_poll()
        self.fake_incoming_with_date('10', self.connection1, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('15', self.connection2, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('12', self.connection3, settings.SCHOOL_TERM_START)
        self.p6_boys_enrolled_poll.end()

        self.poll_for_p6boys_absent = create_poll_with_reporters('edtrac_boysp6_attendance',
                                                  "How many P6 boys are at school today?",
                                                  Poll.TYPE_NUMERIC, self.user,
                                                  [self.emisreporter1, self.emisreporter2, self.emisreporter3])
        self.poll_for_p6boys_absent.save()
        self.poll_for_p6boys_absent.start()
        self.fake_incoming_with_date('5', self.connection1, self.poll_response_current_week_date)
        self.fake_incoming_with_date('4', self.connection2, self.poll_response_current_week_date)
        self.fake_incoming_with_date('3', self.connection3, self.poll_response_current_week_date)

        self.fake_incoming_with_date('1', self.connection1, self.poll_response_past_week_date)
        self.fake_incoming_with_date('7', self.connection2, self.poll_response_past_week_date)
        self.fake_incoming_with_date('2', self.connection3, self.poll_response_past_week_date)

        self.poll_for_p6boys_absent.end()
        result_p6_boys = p6_boys_absent(self.root_node.get_children(), get_time=self.get_time)
        self.assertAlmostEqual(72.97, result_p6_boys['boysp6'], places=1)
        self.assertAlmostEqual(67.56, result_p6_boys['boysp6_past'], places=1)

    def test_percentage_of_p3_boys_absent(self):
        settings.SCHOOL_HOLIDAYS = []
        self.start_p3_boys_enrollment_poll()
        self.fake_incoming_with_date('12', self.connection1, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('10', self.connection2, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('12', self.connection3, settings.SCHOOL_TERM_START)
        self.p3_boys_enrolled_poll.end()

        self.poll_for_p3boys_absent = create_poll_with_reporters('edtrac_boysp3_attendance',
                                                  "How many P3 boys are at school today?",
                                                  Poll.TYPE_NUMERIC, self.user,
                                                  [self.emisreporter1, self.emisreporter2, self.emisreporter3])
        self.poll_for_p3boys_absent.save()

        self.poll_for_p3boys_absent.start()
        self.fake_incoming_with_date('8', self.connection1, self.poll_response_current_week_date)
        self.fake_incoming_with_date('6', self.connection2, self.poll_response_current_week_date)
        self.fake_incoming_with_date('4', self.connection3, self.poll_response_current_week_date)

        self.fake_incoming_with_date('5', self.connection1, self.poll_response_past_week_date)
        self.fake_incoming_with_date('5', self.connection2, self.poll_response_past_week_date)
        self.fake_incoming_with_date('5', self.connection3, self.poll_response_past_week_date)
        self.poll_for_p3boys_absent.end()

        result_p3_boys = p3_absent_boys(self.root_node.get_children(), self.get_time)
        self.assertAlmostEqual(55.88, result_p3_boys['boysp3'], places=1)
        self.assertAlmostEqual(47.05, result_p3_boys['boysp3_past'], places=1)

    def test_percentage_of_p6_girls_absent(self):
        settings.SCHOOL_HOLIDAYS = []
        self.start_p6_girls_enrollment_poll()
        self.fake_incoming_with_date('14', self.connection1, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('10', self.connection2, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('12', self.connection3, settings.SCHOOL_TERM_START)
        self.p6_girls_enrolled_poll.end()

        self.poll_for_p6girls_absent = create_poll_with_reporters('edtrac_girlsp6_attendance',
                                                   "How many P6 girls are at school today?",
                                                   Poll.TYPE_NUMERIC, self.user,
                                                   [self.emisreporter1, self.emisreporter2, self.emisreporter3])
        self.poll_for_p6girls_absent.save()

        self.poll_for_p6girls_absent.start()
        self.fake_incoming_with_date('0', self.connection1, self.poll_response_current_week_date)
        self.fake_incoming_with_date('10', self.connection2, self.poll_response_current_week_date)
        self.fake_incoming_with_date('7', self.connection3, self.poll_response_current_week_date)

        self.fake_incoming_with_date('5', self.connection1, self.poll_response_past_week_date)
        self.fake_incoming_with_date('5', self.connection2, self.poll_response_past_week_date)
        self.fake_incoming_with_date('5', self.connection3, self.poll_response_past_week_date)
        self.poll_for_p6girls_absent.end()

        result_p6_girls = p6_girls_absent(self.root_node.get_children(), get_time=self.get_time)
        self.assertAlmostEqual(58.33, result_p6_girls['girlsp6'], places=1)
        self.assertAlmostEqual(52.77, result_p6_girls['girlsp6_past'], places=1)

    def test_percentage_of_p3_girls_absent(self):
        settings.SCHOOL_HOLIDAYS = []
        self.start_p3_girls_enrollment_poll()
        self.fake_incoming_with_date('8', self.connection1, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('16', self.connection2, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('10', self.connection3, settings.SCHOOL_TERM_START)
        self.p3_girls_enrolled_poll.end()

        self.poll_for_p3girls_absent = create_poll_with_reporters('edtrac_girlsp3_attendance',
                                                   "How many P3 girls are at school today?",
                                                   Poll.TYPE_NUMERIC, self.user,
                                                   [self.emisreporter1, self.emisreporter2, self.emisreporter3])
        self.poll_for_p3girls_absent.save()

        self.poll_for_p3girls_absent.start()
        self.fake_incoming_with_date('2', self.connection1, self.poll_response_current_week_date)
        self.fake_incoming_with_date('1', self.connection2, self.poll_response_current_week_date)
        self.fake_incoming_with_date('3', self.connection3, self.poll_response_current_week_date)

        self.fake_incoming_with_date('5', self.connection1, self.poll_response_past_week_date)
        self.fake_incoming_with_date('5', self.connection2, self.poll_response_past_week_date)
        self.fake_incoming_with_date('5', self.connection3, self.poll_response_past_week_date)
        self.poll_for_p3girls_absent.end()

        result_p3_girls = p3_absent_girls(self.root_node.get_children(), get_time=self.get_time)
        self.assertAlmostEqual(55.88, result_p3_girls['girlsp3'], places=1)
        self.assertAlmostEqual(82.35, result_p3_girls['girlsp3_past'], places=1)

    def test_percentage_of_f_teachers_absent(self):
        settings.SCHOOL_HOLIDAYS = []
        self.start_f_teacher_deployment_poll()
        self.fake_incoming_with_date('10', self.connection1, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('12', self.connection2, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('14', self.connection3, settings.SCHOOL_TERM_START)
        self.f_teacher_deployment_poll.end()

        self.f_teacher_absent_poll=create_poll_with_reporters("edtrac_f_teachers_attendance",
                                               "How many female teachers are at school today?",
                                               Poll.TYPE_NUMERIC,self.user,
                                               [self.emisreporter1,self.emisreporter2,self.emisreporter3])
        self.f_teacher_absent_poll.save()
        self.f_teacher_absent_poll.start()
        self.fake_incoming_with_date('5', self.connection1, self.poll_response_current_week_date)
        self.fake_incoming_with_date('3', self.connection2, self.poll_response_current_week_date)
        self.fake_incoming_with_date('2', self.connection3, self.poll_response_current_week_date)

        self.fake_incoming_with_date('1', self.connection1, self.poll_response_past_week_date)
        self.fake_incoming_with_date('6', self.connection2, self.poll_response_past_week_date)
        self.fake_incoming_with_date('0', self.connection3, self.poll_response_past_week_date)
        self.f_teacher_absent_poll.end()
        result_f_teachers=f_teachers_absent(self.root_node.get_children(), get_time=self.get_time)
        self.assertAlmostEqual(80.55,result_f_teachers['female_teachers'],places=1)
        self.assertAlmostEqual(72.22,result_f_teachers['female_teachers_past'],places=1)

    def test_percentage_of_m_teachers_absent(self):
        settings.SCHOOL_HOLIDAYS = []
        self.start_m_teacher_deployment_poll()
        self.fake_incoming_with_date('13', self.connection1, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('14', self.connection2, settings.SCHOOL_TERM_START)
        self.fake_incoming_with_date('11', self.connection3, settings.SCHOOL_TERM_START)
        self.m_teacher_deployment_poll.end()

        self.m_teacher_absent_poll=create_poll_with_reporters("edtrac_m_teachers_attendance",
                                               "How many male teachers are at school today?",
                                               Poll.TYPE_NUMERIC,self.user,
                                               [self.emisreporter1,self.emisreporter2,self.emisreporter3])
        self.m_teacher_absent_poll.save()
        self.m_teacher_absent_poll.start()
        self.fake_incoming_with_date('8', self.connection1, self.poll_response_current_week_date)
        self.fake_incoming_with_date('2', self.connection2, self.poll_response_current_week_date)
        self.fake_incoming_with_date('1', self.connection3, self.poll_response_current_week_date)

        self.fake_incoming_with_date('5', self.connection1, self.poll_response_past_week_date)
        self.fake_incoming_with_date('6', self.connection2, self.poll_response_past_week_date)
        self.fake_incoming_with_date('3', self.connection3, self.poll_response_past_week_date)
        self.m_teacher_absent_poll.end()
        result_m_teachers=m_teachers_absent(self.root_node.get_children(), self.get_time)
        self.assertAlmostEqual(63.15,result_m_teachers['male_teachers'],places=1)
        self.assertAlmostEqual(71.05,result_m_teachers['male_teachers_past'],places=1)

    def test_male_and_female_head_teachers_attendance(self):

        params = {
            "description": "A response value for a Poll with expected text responses",
            "datatype": "text",
            "enum_group": None,
            "required": False,
            "type": None,
            "slug": "poll_text_value",
            "name": "Text"
        }
        Attribute.objects.create(**params)

        settings.SCHOOL_HOLIDAYS = []
        self.create_emisreporters_of_smc_group()
        self.m_head_teachers_attendance_poll=create_poll_with_reporters("edtrac_head_teachers_attendance",
                                                         "Has the head teacher been at school for at least 3 days? Answer YES or NO",
                                                         Poll.TYPE_TEXT,self.user,
                                                         [self.emisreporter4,self.emisreporter5,self.emisreporter6])

        self.m_head_teachers_attendance_poll.add_yesno_categories()
        self.m_head_teachers_attendance_poll.save()
        self.m_head_teachers_attendance_poll.start()
        self.fake_incoming_with_date('yes', self.connection4, self.poll_response_current_week_date)
        self.fake_incoming_with_date('yes', self.connection5, self.poll_response_current_week_date)
        self.fake_incoming_with_date('no', self.connection6, self.poll_response_current_week_date)

        self.fake_incoming_with_date('no', self.connection4, self.poll_response_past_week_date)
        self.fake_incoming_with_date('no', self.connection5, self.poll_response_past_week_date)
        self.fake_incoming_with_date('yes', self.connection6, self.poll_response_past_week_date)
        result_m_head_teachers=head_teachers_male(self.root_node.get_children(), self.get_time)
        result_f_head_teachers=head_teachers_female(self.root_node.get_children(), self.get_time)

        self.assertAlmostEqual(100.00,result_m_head_teachers['m_head_t_week'],places=1)
        self.assertAlmostEqual(0.00,result_m_head_teachers['m_head_t_week_before'],places=1)

        self.assertAlmostEqual(50.00,result_f_head_teachers['f_head_t_week'],places=1)
        self.assertAlmostEqual(50.00,result_f_head_teachers['f_head_t_week_before'],places=1)

    def test_male_and_female_head_teachers_attendance_on_holiday(self):
        d1,d2 = get_week_date(depth = 2)
        settings.SCHOOL_HOLIDAYS = [(d1[0],d1[1]) , (d2[0],d2[1])]
        self.create_emisreporters_of_smc_group()
        self.m_head_teachers_attendance_poll=create_poll_with_reporters("edtrac_head_teachers_attendance",
                                                         "Has the head teacher been at school for at least 3 days? Answer YES or NO",
                                                         Poll.TYPE_TEXT,self.user,
                                                         [self.emisreporter4,self.emisreporter5,self.emisreporter6])

        self.m_head_teachers_attendance_poll.add_yesno_categories()
        self.m_head_teachers_attendance_poll.save()
        self.m_head_teachers_attendance_poll.start()
        self.fake_incoming_with_date('yes', self.connection4, self.poll_response_current_week_date)
        self.fake_incoming_with_date('yes', self.connection5, self.poll_response_current_week_date)
        self.fake_incoming_with_date('no', self.connection6, self.poll_response_current_week_date)

        self.fake_incoming_with_date('no', self.connection4, self.poll_response_past_week_date)
        self.fake_incoming_with_date('no', self.connection5, self.poll_response_past_week_date)
        self.fake_incoming_with_date('yes', self.connection6, self.poll_response_past_week_date)
        result_m_head_teachers=head_teachers_male(self.root_node.get_children())
        result_f_head_teachers=head_teachers_female(self.root_node.get_children())

        self.assertEqual("--",result_m_head_teachers['m_head_t_week_before'])
        self.assertEqual("--",result_f_head_teachers['f_head_t_week_before'])

    def test_yes_percentage_at_uganda_level(self):
        self.start_upe_poll()
        self.fake_incoming("yes", self.connection1)
        self.fake_incoming("yes", self.connection1)
        self.fake_incoming("no", self.connection2)
        grants = capitation_grants(self.root_node.get_children())
        self.assertAlmostEqual(33.33, grants['grant_percent'], places=1)

    def test_yes_percentage_at_district_level(self):
        self.start_upe_poll()
        self.fake_incoming("yes", self.connection1)
        self.fake_incoming("yes", self.connection3)
        grants = capitation_grants([self.kampala_district])
        self.assertAlmostEqual(50.0, grants['grant_percent'], places=1)

    def test_number_of_valid_schools(self):
        grp = ['Teachers', 'Head Teachers', 'SMC', 'GEM', 'Other Reporters',
               'DEO', 'MEO']
        total_school = schools_valid(self.root_node.get_children(), grp, [])
        self.assertEqual(2, total_school['total_schools_valid'])

    def test_number_of_valid_reporters(self):
        grp = ['Teachers', 'Head Teachers', 'SMC', 'GEM', 'Other Reporters',
               'DEO', 'MEO']
        total_reporter = total_reporters(self.root_node.get_children(), grp, [])
        self.assertEqual(3, total_reporter['total_reporters'])

    def fake_incoming(self, message, connection):
        router = get_router()
        return router.handle_incoming(connection.backend.name, connection.identity, message)

    def fake_incoming_with_date(self, message, connection, date):
        handled = self.fake_incoming(message, connection)
        for response in handled.poll_responses.all():
            response.date = date
            response.save()

        return handled

    def tearDown(self):
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        School.objects.all().delete()
        EmisReporter.objects.all().delete()
        Connection.objects.all().delete()
        Backend.objects.all().delete()
        Poll.objects.all().delete()
        Response.objects.all().delete()
        User.objects.all().delete()
        Group.objects.all().delete()
        Attribute.objects.all().delete()
