# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import random
import datetime
import dateutils
from django.test import Client
from django.conf import settings
from education.models import create_record_enrolled_deployed_questions_answered, EnrolledDeployedQuestionsAnswered
from education.test.abstract_clases_for_tests import TestAbsenteeism
from education.test.utils import *



class TestDashboardAbsenteeism(TestAbsenteeism):

    def test_for_absenteeism_drilled_down(self):
        settings.SCHOOL_TERM_START = dateutils.increment(datetime.datetime.now(),weeks = -2)
        settings.SCHOOL_TERM_END = dateutils.increment(datetime.datetime.now(),weeks = 2)
        create_attribute()
        client = Client()
        client.login(username='John', password='password')
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10',self.emis_reporter1)
        self.fake_incoming('10',self.emis_reporter2)
        self.p3_boys_enrolled_poll.end()
        self.p3_boys_absent_poll.start()
        self.fake_incoming('5',self.emis_reporter1)
        self.fake_incoming('0',self.emis_reporter2)
        create_record_enrolled_deployed_questions_answered(model = EnrolledDeployedQuestionsAnswered)
        response = client.get('/edtrac/attd/boys-p3/')
        self.assertTrue([self.kampala_district, 75.0, 100.0, -25.0] in response.context['location_data'])


    def test_for_absenteeism_over_time_period(self):
        client = Client()
        client.login(username='John',password='password')
        create_attribute()
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10',self.emis_reporter1)
        self.fake_incoming('10',self.emis_reporter2)
        self.p3_boys_enrolled_poll.end()
        self.p3_boys_absent_poll.start()
        self.fake_incoming('5',self.emis_reporter1)
        self.fake_incoming('0',self.emis_reporter2)
        create_record_enrolled_deployed_questions_answered(model = EnrolledDeployedQuestionsAnswered)
        self.set_date(self.p3_boys_enrolled_poll)
        self.set_date(self.p3_boys_absent_poll)
        response = client.post('/edtrac/attd/boys-p3/', {'from_date': getattr(settings, 'SCHOOL_TERM_START').strftime('%m/%d/%Y') , 'to_date': getattr(settings, 'SCHOOL_TERM_END').strftime('%m/%d/%Y')})
        kampala_dataset = response.context['dataset'][0]
        self.assertTrue(self.kampala_district in kampala_dataset)
        self.assertTrue(75.0 in kampala_dataset[1])



    def set_date(self, poll):
        for response in poll.responses.all():
            s = getattr(settings, 'SCHOOL_TERM_START').toordinal()
            e = getattr(settings, 'SCHOOL_TERM_END').toordinal()
            response.date = datetime.datetime.fromordinal(random.randint(s,e))
            response.save()



