from datetime import datetime
from unittest import TestCase
from django.contrib.auth.models import User
from django.core import management
from django.core.urlresolvers import reverse
from django.test import Client
from education.test.utils import create_user_with_group
from education.water_polls_views import schedule_water_polls, ScheduleWaterPollForm
from poll.models import Poll
from script.models import Script, ScriptStep


class TestWaterPollsViews(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_user_with_group('admin')
        management.call_command('create_water_polls_and_scripts')

    def test_should_have_water_polls_in_context_of_schedule_view(self):
        self.client.login(username=self.user.username,password='password')
        response = self.client.get(reverse(schedule_water_polls))
        self.assertEqual(200, response.status_code)

    def test_should_enforce_login_on_schedule_water_poll_view(self):
        response = self.client.get(reverse(schedule_water_polls))
        self.assertEqual(302, response.status_code)

    def test_should_throw_error_if_date_less_than_today(self):
        now = datetime.now()
        params = dict(on_date_day=now.day-1,on_date_year=now.year,on_date_month=now.month)
        form = ScheduleWaterPollForm(params)
        self.assertFalse(form.is_valid())
        self.assertTrue('on_date' in form.errors)

    def test_should_allow_valid_date(self):
        now = datetime.now()
        params = dict(on_date_day=now.day,on_date_year=now.year,on_date_month=now.month)
        form = ScheduleWaterPollForm(params)
        self.assertTrue(form.is_valid())


    def tearDown(self):
        User.objects.all().delete()
        ScriptStep.objects.all().delete()
        Script.objects.all().delete()
        Poll.objects.all().delete()
