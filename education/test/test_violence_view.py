# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import datetime
import random
import dateutils
from django.contrib.auth.models import Group
from django.db.models import F
from education.models import schedule_script_now, EmisReporter
from education.test.abstract_clases_for_tests import TestSetup
from education.test.utils import create_attribute
from django.test.client import Client
from poll.models import Poll
from script.models import Script, ScriptStep, ScriptProgress, ScriptSession
from script.signals import script_progress_pre_change, script_progress

class TestViolenceView(TestSetup):
    def setUp(self):
        super(TestViolenceView, self).setUp()
        self.client=Client()
        self.client.login(username='John', password='password')
        self.add_group([self.emisreporter1, self.emisreporter2, self.emisreporter3],
                       Group.objects.create(name='Head Teachers'))
        create_attribute()
        self.script = Script.objects.create(slug="edtrac_headteacher_violence_monthly",
                                            name="Headteacher Violence Monthly Script",
                                            enabled=False)
        polls = ["edtrac_violence_girls", "edtrac_violence_boys", "edtrac_violence_reported", "edtrac_gem_abuse"]
        poll_questions = ["How many cases of violence against girls were recorded this month? Answer in figures e.g. 5",
                          "How many cases of violence against boys were recorded this month? Answer in figures e.g. 4",
                          "How many cases of violence were referred to the Police this month? Answer in figures e.g. 6",
                          "How many violence cases were reported to you this month?"]
        for poll, poll_question in zip(polls, poll_questions):
            self.create_poll(poll, self.admin_user, Poll.TYPE_NUMERIC, poll_question, '')
            self.script.steps.add(
                ScriptStep.objects.create(script=self.script, poll=self.violence_poll, order=polls.index(poll),
                                          rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=86400, ))
        schedule_script_now('Head Teachers','edtrac_headteacher_violence_monthly')

    def test_violence_cases_for_boys(self):
        responses, kampala_response, gulu_response = self.get_fake_responses_for_each_month_till_date_for_a_given_poll(
            "edtrac_violence_boys")
        request = self.client.get('/edtrac/violence-admin-details/')
        self.assert_each_response_for_last_two_months(kampala_response,gulu_response,request.context["violence_cases_boys"])
        months, violence_cases = self.split_data(request.context['monthly_violence_data_boys'])
        for month, violence_case, response in zip(months, violence_cases, responses):
            self.assertEqual(datetime.datetime.strptime(month, "%B").month, months.index(month) + 1)
            self.assertEqual(response, violence_case)

    def test_violence_cases_for_reporters(self):
        responses, kampala_response, gulu_response = self.get_fake_responses_for_each_month_till_date_for_a_given_poll(
            "edtrac_violence_reported")
        request = self.client.get('/edtrac/violence-admin-details/')
        self.assert_each_response_for_last_two_months(kampala_response,gulu_response,request.context["violence_cases_reported"])
        months, violence_cases = self.split_data(request.context['monthly_violence_data_reported'])
        for month, violence_case, response in zip(months, violence_cases, responses):
            self.assertEqual(datetime.datetime.strptime(month, "%B").month, months.index(month) + 1)
            self.assertEqual(response, violence_case)

    def test_violence_cases_for_gem_abuses(self):
        responses, kampala_response, gulu_response = self.get_fake_responses_for_each_month_till_date_for_a_given_poll(
            "edtrac_gem_abuse")
        request = self.client.get('/edtrac/violence-admin-details/')
        self.assert_each_response_for_last_two_months(kampala_response,gulu_response,request.context["violence_cases_reported_by_gem"])
        months, violence_cases = self.split_data(request.context['monthly_data_gem'])
        for month, violence_case, response in zip(months, violence_cases, responses):
            self.assertEqual(datetime.datetime.strptime(month, "%B").month, months.index(month) + 1)
            self.assertEqual(response, violence_case)

    def test_violence_cases_for_girls(self):
        responses,kampala_response,gulu_response = self.get_fake_responses_for_each_month_till_date_for_a_given_poll("edtrac_violence_girls")
        request = self.client.get('/edtrac/violence-admin-details/')
        self.assert_each_response_for_last_two_months(kampala_response,gulu_response,request.context["violence_cases_girls"])
        months, violence_cases = self.split_data(request.context['monthly_violence_data_girls'])
        for month, violence_case, response in zip(months, violence_cases, responses):
            self.assertEqual(datetime.datetime.strptime(month, "%B").month, months.index(month) + 1)
            self.assertEqual(response, violence_case)

    def assert_each_response_for_last_two_months(self,kampala_response,gulu_response,responses):
        if self.kampala_district not in responses[0][1]:
            gulu_response,kampala_response=kampala_response,gulu_response
        self.assertEqual(kampala_response[0], responses[0][1][0])
        self.assertEqual(kampala_response[1], responses[0][1][1])
        self.assertEqual(gulu_response[0], responses[1][1][0])
        self.assertEqual(gulu_response[1], responses[1][1][1])

    def get_fake_responses_for_each_month_till_date_for_a_given_poll(self, poll):
        response_for_each_month = []
        expected_values,kampala_values,gulu_values = self.generate_fake_responses_for_a_given_poll(poll)
        expected_values.reverse()
        for expected_value in expected_values:
            sum_of_responses = 0
            for value in expected_value:
                sum_of_responses += float(value)
            response_for_each_month.append(sum_of_responses)
        return response_for_each_month,kampala_values,gulu_values

    def generate_fake_responses_for_a_given_poll(self, poll):
        fake_responses = []
        kampala_responses=[]
        gulu_responses=[]
        start_date = datetime.datetime(datetime.datetime.now().year, datetime.datetime.now().month, 15)
        while (start_date.month + 1) != 13:
            self.generate_script_progress_and_session("edtrac_headteacher_violence_monthly", start_date, poll)
            values = self.generate_random_replies()
            fake_responses.append(values)
            if (start_date.month==datetime.datetime.now().month) or (start_date.month==(datetime.datetime.now().month-1)):
                kampala_responses.append(float(values[0])+float(values[1]))
                gulu_responses.append(float(values[2]))
            self.fake_incoming_with_date(values[0], self.connection1, start_date)
            self.fake_incoming_with_date(values[1], self.connection2, start_date)
            self.fake_incoming_with_date(values[2], self.connection3, start_date)
            start_date = dateutils.increment(start_date, months=-1)
        return fake_responses,kampala_responses,gulu_responses

    def generate_random_replies(self):
        random_replies = []
        for reps in EmisReporter.objects.filter(groups__name="Head Teachers"):
            random_replies.append(str(random.randrange(2,20)))
        return random_replies

    def generate_script_progress_and_session(self, slug, date, poll):
        script_progress_list = list(ScriptProgress.objects.all().values_list('pk', flat=True))
        ScriptProgress.objects.filter(script=self.script).filter(
            connection__contact__emisreporter__groups__name__iexact="Head Teachers").delete()
        reps = EmisReporter.objects.filter(groups__name="Head Teachers")
        for rep in reps:
            if rep.default_connection and rep.groups.count() > 0:
                sp = ScriptProgress.objects.create(connection=rep.default_connection,
                                                   script=Script.objects.get(slug=slug))
                sp.set_time(date)
        ScriptProgress.objects.filter(connection=rep.default_connection).filter(num_tries=None).update(num_tries=0)
        ScriptProgress.objects.filter(connection=rep.default_connection).update(num_tries=F('num_tries') + 1,
                                                                                time=datetime.datetime.now())
        for sp in ScriptProgress.objects.all():
            ScriptSession.objects.create(script=sp.script, connection=sp.connection)
            script_progress_pre_change.send(sender=sp, connection=sp.connection, step=None)
        ScriptProgress.objects.filter(script=self.script).update(step=ScriptStep.objects.get(poll__name=poll),
                                                                 status=ScriptProgress.PENDING,
                                                                 time=datetime.datetime.now())
        for sp in ScriptProgress.objects.all().model._default_manager.filter(pk__in=script_progress_list):
            script_progress.send(sender=sp, connection=sp.connection,
                                 step=ScriptStep.objects.filter(poll__name="edtrac_violence_girls"))

    def split_data(self, monthly_data):
        monthly_data_collection = monthly_data.split(';')
        months = []
        violence_cases = []

        for data in monthly_data_collection:
            split_data = data.split('-')
            months.append(split_data[0])
            violence_cases.append(float(split_data[1]))
        return months, violence_cases