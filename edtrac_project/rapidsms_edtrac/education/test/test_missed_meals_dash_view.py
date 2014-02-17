from unittest import TestCase
from rapidsms.contrib.locations.models import Location
from rapidsms.contrib.locations.models import LocationType
from django.contrib.auth.models import Group
from education.models import schedule_script_now
from education.test.utils import *
from education.views import meals_missed
from poll.models import Poll
from rapidsms_httprouter.models import Message
from script.models import Script, ScriptStep, ScriptProgress
from script.utils.outgoing import check_progress

class TestMealsMissedDetailsDashView(TestCase):
    def setUp(self):
        district = create_location_type("district")
        self.kampala_district = create_location("Kampala", district)
        kampala_school = create_school("St. Joseph's", self.kampala_district)

        self.head_teacher_group = create_group("Head Teachers")
        self.emis_reporter1 = create_emis_reporters("dummy1", self.kampala_district, kampala_school, 12904,
                                               self.head_teacher_group)
        self.emis_reporter1.grade = 'P3'
        self.emis_reporter1.save()

        self.admin_group = create_group("Admins")
        self.admin_user = create_user_with_group("John", self.admin_group, self.kampala_district)

        self.meals_poll = create_poll_with_reporters("edtrac_headteachers_meals",
                                                     "How many students missed school meals?",
                                                     Poll.TYPE_NUMERIC, self.admin_user,
                                                     [self.emis_reporter1])

        self.head_teachers_script = Script.objects.create(name="Headteacher Monthly Script",
                                                   slug="edtrac_headteacher_monthly")
        self.head_teachers_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_script, poll=self.meals_poll, order=0,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=2)
        )

        create_attribute()


    def test_counts_schools_with_all_meals_missed(self):
        schedule_script_now(self.head_teacher_group.name, slug=self.head_teachers_script.slug)
        check_progress(self.head_teachers_script)
        fake_incoming('0%', self.emis_reporter1)
        self.assertEquals({"meals_missed": 1}, meals_missed([self.kampala_district], datetime.datetime.now))

    def tearDown(self):
        Message.objects.all().delete()
        ScriptProgress.objects.all().delete()
        ScriptStep.objects.all().delete()
        ScriptSession.objects.all().delete()
        Script.objects.all().delete()
        Poll.objects.all().delete()
        EmisReporter.objects.all().delete()
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        School.objects.all().delete()
        User.objects.all().delete()
        Group.objects.all().delete()
