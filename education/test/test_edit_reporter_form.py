# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from mock import Mock
from education.forms import EditReporterForm
from education.models import EmisReporter, School
from education.test.utils import create_location, create_location_type, create_school
from rapidsms.contrib.locations.models import Location, LocationType


class TestEditReporterForm(TestCase):
    def setUp(self):
        district_type = create_location_type('district')
        county_type = create_location_type('county')
        self.kampala_district = create_location('kampala', district_type)
        self.masaka_district= create_location('masaka', district_type)
        self.kasese_county = create_location('kasese',county_type)
        self.emis_reporter = EmisReporter.objects.create(name="Akshay Naval")
        self.school1 = create_school("Standard High School", self.kampala_district)
        self.school2 = create_school("Makerere College School", self.kampala_district)
        self.school3 = create_school("St. Henry's College Kitovu", self.masaka_district)

    def test_query_for_reporter_with_no_location_and_no_school(self):
        l = Location.objects.filter(type="district").order_by('name')
        edit_emis_reporter_form = EditReporterForm(instance=self.emis_reporter)
        self.assertEqual(str(l.query),str(edit_emis_reporter_form.fields['reporting_location'].queryset.query))

    def test_result_for_reporter_with_no_location_and_no_school(self):
        edit_emis_reporter_form = EditReporterForm(instance=self.emis_reporter)
        self.assertEqual([self.kampala_district,self.masaka_district],list(edit_emis_reporter_form.fields['reporting_location'].queryset))

    def test_result_for_reporter_with_location_but_no_school(self):
        self.emis_reporter.reporting_location = self.kampala_district
        self.emis_reporter.save()
        edit_emis_reporter_form = EditReporterForm(instance=self.emis_reporter)
        self.assertEqual([self.kampala_district,self.masaka_district],list(edit_emis_reporter_form.fields['reporting_location'].queryset))
        self.assertTrue(self.school1 in list(edit_emis_reporter_form.fields['schools'].queryset))
        self.assertTrue(self.school2 in list(edit_emis_reporter_form.fields['schools'].queryset))
        self.assertFalse(self.school3 in list(edit_emis_reporter_form.fields['schools'].queryset))

    def test_result_for_reporter_with_no_location_but_school(self):
        self.emis_reporter.schools.add(self.school1)
        self.emis_reporter.save()
        edit_emis_reporter_form = EditReporterForm(instance=self.emis_reporter)
        self.assertEqual([self.kampala_district,self.masaka_district],list(edit_emis_reporter_form.fields['reporting_location'].queryset))
        self.assertTrue(self.school1 in list(edit_emis_reporter_form.fields['schools'].queryset))
        self.assertFalse(self.school2 in list(edit_emis_reporter_form.fields['schools'].queryset))
        self.assertFalse(self.school3 in list(edit_emis_reporter_form.fields['schools'].queryset))

    def test_result_for_reporter_with_both_location_and_schools(self):
        self.emis_reporter.reporting_location = self.kampala_district
        self.emis_reporter.schools.add(self.school1)
        self.emis_reporter.save()
        edit_emis_reporter_form = EditReporterForm(instance=self.emis_reporter)
        self.assertTrue(self.kampala_district in edit_emis_reporter_form.fields['reporting_location'].queryset)
        self.assertTrue(self.masaka_district in edit_emis_reporter_form.fields['reporting_location'].queryset)
        self.assertFalse(self.kasese_county in edit_emis_reporter_form.fields['reporting_location'].queryset)
        self.assertTrue(self.school1 in edit_emis_reporter_form.fields['schools'].queryset)
        self.assertTrue(self.school2 in edit_emis_reporter_form.fields['schools'].queryset)
        self.assertFalse(self.school3 in edit_emis_reporter_form.fields['schools'].queryset)

    def test_result_for_reporter_with_location_different_than_school_location(self):
        self.emis_reporter.reporting_location = self.kampala_district
        self.emis_reporter.schools.add(self.school3)
        self.emis_reporter.save()
        edit_emis_reporter_form = EditReporterForm(instance=self.emis_reporter)
        self.assertEqual([self.kampala_district,self.masaka_district],list(edit_emis_reporter_form.fields['reporting_location'].queryset))
        self.assertTrue(self.school1 in edit_emis_reporter_form.fields['schools'].queryset)
        self.assertTrue(self.school2 in edit_emis_reporter_form.fields['schools'].queryset)
        self.assertTrue(self.school3 in edit_emis_reporter_form.fields['schools'].queryset)

    def test_should_not_save_when_school_is_in_wrong_location(self):
        self.emis_reporter.reporting_location = self.kampala_district
        self.emis_reporter.schools.add(self.school3)
        self.emis_reporter.save()
        edit_emis_reporter_form = EditReporterForm(
            instance=self.emis_reporter, data={'reporting_location':self.kampala_district.id,'schools':self.school3.id})
        self.assertFalse(edit_emis_reporter_form.is_valid())
        self.assertTrue("schools" in edit_emis_reporter_form._errors.keys())

    def tearDown(self):
        LocationType.objects.all().delete()
        Location.objects.all().delete()
        EmisReporter.objects.all().delete()