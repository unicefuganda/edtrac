from unittest import TestCase
from education.scheduling import *
from datetime import date
from rapidsms.models import Connection, Backend, Contact
from django.contrib.auth.models import Group
from script.models import Script, ScriptProgress
from education.models import EmisReporter
from unregister.models import Blacklist

class TestScheduling(TestCase):

    def test_finds_upcoming_date(self):
        today = date(2013, 12, 29)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals(date(2014, 1, 2), upcoming(dates, get_day = lambda: today))

    def test_current_date_doesnt_count_as_upcoming(self):
        today = date(2013, 12, 26)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals(date(2014, 1, 2), upcoming(dates, get_day = lambda: today))

    def test_finds_when_no_upcoming_date(self):
        today = date(2014, 1, 29)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals(None, upcoming(dates, get_day = lambda: today))

    def test_finds_current_period(self):
        today = date(2013, 12, 29)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals((date(2013, 12, 26),date(2014, 1, 1)), current_period(dates, get_day = lambda: today))

    def test_finds_current_period_with_open_end(self):
        today = date(2014, 1, 29)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals((date(2013, 12, 26),None), current_period(dates, get_day = lambda: today))

    def test_finds_current_period_with_open_start(self):
        today = date(2013, 11, 29)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals((None,date(2013, 12, 25)), current_period(dates, get_day = lambda: today))

    def test_finds_upcoming_date_and_time_for_specific_poll(self):
        roster = {'p6_girls': [date(2013, 8, 29), date(2013, 9, 4)],
                  'p3_girls': [date(2013, 3, 29), date(2013, 4, 4)]}

        today = date(2013, 3, 30)

        self.assertEquals(datetime(2013, 4, 4, 10, 0, 0), next_scheduled('p3_girls', roster = roster, get_day = lambda: today))

    def test_finds_when_no_upcoming_date_and_time_for_specific_poll(self):
        today = date(2013, 3, 30)
        self.assertEquals(None, next_scheduled('p3_girls', roster = {}, get_day = lambda: today))

    def test_finds_next_scheduled_poll(self):
       roster = {'p6_girls': [date(2013, 8, 29)]}
       today = date(2013, 8, 23)
       self.assertEquals(datetime(2013, 8, 29, 10, 0, 0), next_scheduled('p6_girls', roster=roster, get_day=lambda: today))

    def test_schedules_poll_for_connection(self):
       roster = {'p6_girls': [date(2013, 8, 29)]}
       today = date(2013, 8, 23)

       script = Script.objects.create(slug='p6_girls')
       backend = Backend.objects.create(name='foo')
       connection = Connection.objects.create(backend=backend)
       current = ScriptProgress.objects.create(connection=connection, script=script)

       schedule(connection, script, roster=roster, get_day=lambda: today)
       future = ScriptProgress.objects.get(connection=connection, script=script)

       self.assertEquals(datetime(2013, 8, 29, 10, 0, 0), future.time)

    def test_doesnt_schedule_blacklisted_connections(self):
       roster = {'p6_girls': [date(2013, 8, 29)]}
       today = date(2013, 8, 23)

       script = Script.objects.create(slug='p6_girls')
       backend = Backend.objects.create(name='foo')
       connection = Connection.objects.create(backend=backend)
       Blacklist.objects.create(connection=connection)
       current = ScriptProgress.objects.create(connection=connection, script=script)

       schedule(connection, script, roster=roster, get_day=lambda: today)
       future_scheduled = ScriptProgress.objects.filter(connection=connection, script=script).exists()

       self.assertFalse(future_scheduled)

    def test_schedules_all_polls_for_connection(self):
       roster = {'p6_girls': [date(2013, 8, 29)]}
       groups = {'Teachers': ['p6_girls']}
       today = date(2013, 8, 23)

       script = Script.objects.create(name='edtrac_p6_girls', slug='p6_girls')
       reporter = EmisReporter.objects.create(grade='P6')
       backend = Backend.objects.create(name='foo')
       contact = Contact.objects.create()
       contact.emisreporter = reporter
       contact.save()
       connection = Connection.objects.create(backend=backend, contact=contact)
       connection.contact.groups.add(Group.objects.create(name='Teachers'))
       connection.save()
       current = ScriptProgress.objects.create(connection=connection, script=script)

       schedule_all(connection, groups=groups, roster=roster, get_day=lambda: today)
       future = ScriptProgress.objects.get(connection=connection, script=script)

       self.assertEquals(datetime(2013, 8, 29, 10, 0, 0), future.time)

    def test_schedules_at_specified_time(self):
       time = datetime(2013, 8, 23, 11, 33)

       script = Script.objects.create(slug='p6_girls')
       backend = Backend.objects.create(name='foo')
       connection = Connection.objects.create(backend=backend)
       current = ScriptProgress.objects.create(connection=connection, script=script)

       schedule_at(connection, script, time)
       future = ScriptProgress.objects.get(connection=connection, script=script)

       self.assertEquals(datetime(2013, 8, 23, 11, 33), future.time)

    def test_scripts_are_derived_from_a_connections_groups(self):
       groups = {'Head Teachers': ['water points']}

       reporter = EmisReporter.objects.create()
       backend = Backend.objects.create(name='foo')
       contact = Contact.objects.create()
       contact.emisreporter = reporter
       contact.save()
       connection = Connection.objects.create(backend=backend, contact=contact)
       connection.contact.groups.add(Group.objects.create(name='Head Teachers'))
       connection.save()

       script_slugs = scripts_for(connection, groups=groups)

       self.assertEquals(['water points'], script_slugs)

    def test_teachers_belong_to_virtual_groups_with_their_grade(self):
       groups = {'p6': ['p6_girls']}

       reporter = EmisReporter.objects.create(grade='P6')
       backend = Backend.objects.create(name='foo')
       contact = Contact.objects.create()
       contact.emisreporter = reporter
       contact.save()
       connection = Connection.objects.create(backend=backend, contact=contact)
       connection.contact.groups.add(Group.objects.create(name='Teachers'))
       connection.save()

       script_slugs = scripts_for(connection, groups=groups)

       self.assertEquals(['p6_girls'], script_slugs)


    def test_schedules_all_connections_for_a_script(self):
       groups = {'Head Teachers': ['p8_girls']}
       roster = {'p8_girls': [date(2013, 8, 29)]}

       script = Script.objects.create(slug='p8_girls')
       backend = Backend.objects.create(name='foo')
       contact = Contact.objects.create()
       contact.groups.add(Group.objects.create(name='Head Teachers'))
       contact.save()
       connection = Connection.objects.create(backend=backend, contact=contact)

       schedule_script(script, roster=roster, get_day=lambda: date(2013, 8, 28), groups=groups)
       future = ScriptProgress.objects.get(connection=connection, script=script)

       self.assertEquals(datetime(2013, 8, 29, 10, 0, 0), future.time)

    def test_schedules_all_connections_for_a_script_at_the_specified_time(self):
       groups = {'Head Teachers': ['p7_girls']}

       script = Script.objects.create(slug='p7_girls')
       backend = Backend.objects.create(name='foo')
       contact = Contact.objects.create()
       contact.groups.add(Group.objects.create(name='Head Teachers'))
       contact.save()
       connection = Connection.objects.create(backend=backend, contact=contact)

       schedule_script_at(script, datetime(2013, 8, 28, 11, 0, 3), groups=groups)
       future = ScriptProgress.objects.get(connection=connection, script=script)

       self.assertEquals(datetime(2013, 8, 28, 11, 0, 3), future.time)

    def test_schedules_all_teacher_connections_for_a_grade_based_script(self):
       groups = {'p6': ['p6_girls']}

       script = Script.objects.create(slug='p6_girls')
       backend = Backend.objects.create(name='foo')
       contact = Contact.objects.create()
       contact.groups.add(Group.objects.create(name='Teachers'))
       contact.grade = 'p6'
       contact.save()
       connection = Connection.objects.create(backend=backend, contact=contact)

       schedule_script_at(script, datetime(2013, 8, 28, 11, 0, 3), groups=groups)
       future = ScriptProgress.objects.get(connection=connection, script=script)

       self.assertEquals(datetime(2013, 8, 28, 11, 0, 3), future.time)


    def tearDown(self):
        Backend.objects.all().delete()
        Script.objects.all().delete()
        Group.objects.all().delete()
        EmisReporter.objects.all().delete()
