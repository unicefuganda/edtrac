# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import datetime
from unittest import TestCase
import dateutils
from django.contrib.auth.models import Group
from education.models import EmisReporter
from education.templatetags.stats_extras import latest
from education.test.utils import create_location, create_poll_with_reporters, create_user_with_group, create_group, create_emis_reporters, create_location_type
from poll.models import Poll, Response
from rapidsms.contrib.locations.models import LocationType, Location


class TestStatsExtra(TestCase):

    def test_should_return_latest_reporting_date_for_record(self):
        smc = create_group('SMC')
        location = create_location('kampala', create_location_type('district'))
        emis_reporter = create_emis_reporters('reporter1',location,None,12345,smc)
        poll = create_poll_with_reporters('poll1','dummy question',Poll.TYPE_TEXT,create_user_with_group('user1'),[emis_reporter])
        responses1 = Response.objects.create(poll=poll,contact=emis_reporter)
        responses2 = Response.objects.create(poll=poll,contact=emis_reporter)
        responses3 = Response.objects.create(poll=poll,contact=emis_reporter)
        self.set_response_date(responses1,dateutils.increment(datetime.now(),weeks=-1))
        self.set_response_date(responses2,dateutils.increment(datetime.now(),weeks=-2))
        self.set_response_date(responses3,dateutils.increment(datetime.now(),weeks=-3))
        latest_date = latest(emis_reporter)
        self.assertEqual(dateutils.increment(datetime.now(),weeks=-1).date(),latest_date.date())

    def test_should_return_none_if_no_responses_found(self):
        smc = create_group('SMC')
        location = create_location('kampala', create_location_type('district'))
        emisreporter = create_emis_reporters('reporter1',location,None,12345,smc)
        latest_date = latest(emisreporter)
        self.assertEqual(None,latest_date)

    def set_response_date(self,response,date):
        response.date = date
        response.save()

    def tearDown(self):
        Group.objects.all().delete()
        LocationType.objects.all().delete()
        Location.objects.all().delete()
        Poll.objects.all().delete()
        Response.objects.all().delete()
        EmisReporter.objects.all().delete()