"""
Basic tests for XForms
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.test.client import Client
from django.core.exceptions import ValidationError
from .models import XForm, XFormField, XFormFieldConstraint, xform_received
from eav.models import Attribute

class ViewTest(TestCase): # pragma: no cover
    urls = 'rapidsms_xforms.test_urls'

    def setUp(self):
        self.user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
        self.user.save()
        self.client = Client()
        self.client.login(username='fred', password='secret')

    def testAuthenticated(self):
        self.client.logout()
        response = self.client.get("/xforms/")
        self.failUnlessEqual(response.status_code, 302)

    def testList(self):
        x1 = XForm.objects.create(name="form1", keyword="form1", description="nothing", owner=self.user)
        response = self.client.get("/xforms/")
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(len(response.context['xforms']), 1)

    def testNew(self):
        response = self.client.post("/xforms/new/",
                                    { 'name': 'form2',
                                      'keyword': 'keyword2',
                                      'description': 'desc2',
                                      'response': 'response2'}, follow=True)

        self.failUnlessEqual(response.status_code, 200)

        # make sure we have the newly created xform
        xform = response.context['xform']

        self.failUnlessEqual(xform.pk, 1)
        self.failUnlessEqual(xform.name, 'form2')
        self.failUnlessEqual(xform.keyword, 'keyword2')
        self.failUnlessEqual(xform.description, 'desc2')
        self.failUnlessEqual(xform.owner, self.user)


        # check that dupe doesn't work
        response = self.client.post("/xforms/new/",
                                    { 'name': 'form2',
                                      'keyword': 'keyword2',
                                      'description': 'desc2' }, follow=True)
        self.failUnlessEqual(response.status_code, 200)

        # we shouldnt have an xform created
        self.failIf('xform' in response.context)

class ModelTest(TestCase): #pragma: no cover

    def setUp(self):
        self.user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
        self.user.save()

        self.xform = XForm(name='test', keyword='test', owner=self.user)
        self.xform.save()


    def failIfValid(self, constraint, value):
        try:
            constraint.validate(value)
            self.fail("Should have failed validating: %s" % value)
        except ValidationError:
            pass

    def failUnlessValid(self, constraint, value):
        try:
            constraint.validate(value)
        except ValidationError:
            self.fail("Should have passed validating: %s" % value)

    def failIfClean(self, field, value):
        try:
            field.clean_submission(value)
            self.fail("Should have failed cleaning: %s" % value)
        except ValidationError:
            pass

    def failUnlessClean(self, field, value):
        try:
            field.clean_submission(value)
        except ValidationError:
            self.fail("Should have passed cleaning: %s" % value)

    def testMinValConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='min_val', test='10', message=msg)

        self.failIfValid(c, '1')
        self.failUnlessValid(c, None)
        self.failUnlessValid(c, '10')
        self.failUnlessValid(c, '11')

    def testMaxValConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='max_val', test='10', message=msg)

        self.failUnlessValid(c, '1')
        self.failUnlessValid(c, '10')
        self.failUnlessValid(c, None)
        self.failIfValid(c, '11')

    def testMinLenConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='min_len', test='2', message=msg)

        self.failIfValid(c, 'a')
        self.failIfValid(c, '')
        self.failUnlessValid(c, None)
        self.failUnlessValid(c, 'ab')
        self.failUnlessValid(c, 'abcdef')

    def testMaxLenConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='max_len', test='3', message=msg)

        self.failUnlessValid(c, 'a')
        self.failUnlessValid(c, '')
        self.failUnlessValid(c, None)
        self.failUnlessValid(c, 'abc')
        self.failIfValid(c, 'abcdef')

    def testReqValConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='req_val', message=msg)

        self.failUnlessValid(c, 'a')
        self.failUnlessValid(c, '1.20')
        self.failIfValid(c, '')
        self.failIfValid(c, None)

    def testRegexConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='regex', test='^(mal|fev)$', message=msg)

        self.failIfValid(c, 'a')
        self.failIfValid(c, '')
        self.failIfValid(c, 'malo')
        self.failUnlessValid(c, None)
        self.failUnlessValid(c, 'MAL')
        self.failUnlessValid(c, 'FeV')

    def testIntField(self):
        field = self.xform.fields.create(datatype=Attribute.TYPE_INT, name='number', command='number')

        self.failUnlessClean(field, '1 ')
        self.failUnlessClean(field, None)
        self.failUnlessClean(field, '')
        self.failIfClean(field, 'abc')
        self.failIfClean(field, '1.34')

    def testDecField(self):
        field = self.xform.fields.create(datatype=Attribute.TYPE_FLOAT, name='number', command='number')

        self.failUnlessClean(field, '1')
        self.failUnlessClean(field, ' 1.1')
        self.failUnlessClean(field, None)
        self.failUnlessClean(field, '')
        self.failIfClean(field, 'abc')

    def testStrField(self):
        field = self.xform.fields.create(datatype=Attribute.TYPE_TEXT, name='string', command='string')

        self.failUnlessClean(field, '1')
        self.failUnlessClean(field, '1.1')
        self.failUnlessClean(field, 'abc')
        self.failUnlessClean(field, None)
        self.failUnlessClean(field, '')

    def testGPSField(self):
        field = self.xform.fields.create(datatype=Attribute.TYPE_OBJECT, name='location', command='location')

        self.failUnlessClean(field, '1 2')
        self.failUnlessClean(field, '1.1 1')
        self.failUnlessClean(field, '-1.1 -1.123')
        self.failUnlessClean(field, '')
        self.failUnlessClean(field, None)

        self.failIfClean(field, '1.123')
        self.failIfClean(field, '1.123 asdf')
        self.failIfClean(field, 'asdf')
        self.failIfClean(field, '-91.1 -1.123')
        self.failIfClean(field, '92.1 -1.123')
        self.failIfClean(field, '-1.1 -181.123')
        self.failIfClean(field, '2.1 181.123')

    def testFieldConstraints(self):
        field = self.xform.fields.create(datatype=Attribute.TYPE_TEXT, name='number', command='number')

        # test that with no constraings, all values work
        self.failUnlessClean(field, '1')
        self.failUnlessClean(field, None)
        self.failUnlessClean(field, 'abc')

        # now add some constraints
        msg1 = 'error message'
        field.constraints.create(type='min_val', test='10', message=msg1)
        
        self.failIfClean(field, '1')
        self.failIfClean(field, '-1')
        self.failUnlessClean(field, '10')

        # add another constraint
        msg2 = 'error message 2'
        field.constraints.create(type='max_val', test='50', message=msg2)
        self.failIfClean(field, '1')
        self.failUnlessClean(field, '10')
        self.failIfClean(field, '100')

        # another, but set its order to be first
        msg3 = 'error message 3'
        field.constraints.create(type='min_val', test='5', message=msg3, order=0)
        self.failIfClean(field, '1')
        self.failIfClean(field, '6')

class SubmisionTest(TestCase): #pragma: no cover
    
    def setUp(self):
        # bootstrap a form
        self.user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
        self.user.save()

        self.xform = XForm(name='test', keyword='survey', owner=self.user)
        self.xform.save()

        field = self.xform.fields.create(datatype=Attribute.TYPE_TEXT, name='gender', command='gender')
        field.constraints.create(type='req_val', test='None', message="You must include a gender")
        field = self.xform.fields.create(datatype=Attribute.TYPE_INT, name='age', command='age')
        field.constraints.create(type='req_val', test='None', message="You must include an age")
        self.xform.fields.create(datatype=Attribute.TYPE_TEXT, name='name', command='name')

    def testSMSSubmission(self):
        submission = self.xform.process_sms_submission("survey +age 10 +name matt berg +gender male", None)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        # test with just an age and gender
        submission = self.xform.process_sms_submission("survey male 10", None)
        self.failUnlessEqual(len(submission.values.all()), 2)
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)

        # mix of required and not
        submission = self.xform.process_sms_submission("survey male 10 +name matt berg", None)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        # make sure we record errors if there is a missing age
        submission = self.xform.process_sms_submission("survey +name luke skywalker", None)
        self.failUnlessEqual(submission.has_errors, True)
        self.failUnlessEqual(2, len(submission.errors))

        # make sure we record errors if there is just the keyword
        submission = self.xform.process_sms_submission("survey", None)
        self.failUnlessEqual(submission.has_errors, True)
        self.failUnlessEqual(2, len(submission.errors))

    def testSignal(self):
        # add a listener to our signal
        class Listener:
            def handle_submission(self, sender, **args):
                print "FRIKKIN GOT HERE"
                if args['xform'].keyword == 'survey':
                    self.submission = args['submission']
                    self.xform = args['xform']


        listener = Listener()
        xform_received.connect(listener.handle_submission)

        submission = self.xform.process_sms_submission("survey male 10 +name matt berg", None)
        self.failUnlessEqual(listener.submission, submission)
        self.failUnlessEqual(listener.xform, self.xform)

        # test that it works via update as well
        new_vals = { 'age': 20, 'name': 'greg snider' }
        self.xform.update_submission_from_dict(submission, new_vals)

        self.failUnlessEqual(listener.submission.values.get(attribute__name='age').value, 20)
        self.failUnlessEqual(listener.submission.values.get(attribute__name='name').value, 'greg snider')

    def testUpdateFromDict(self):
        submission = self.xform.process_sms_submission("survey male +age 10 +name matt berg", None)
        self.failUnlessEqual(len(submission.values.all()), 3)

        # now update the form using a dict
        new_vals = { 'age': 20, 'name': 'greg snider' }
        self.xform.update_submission_from_dict(submission, new_vals)

        self.failUnlessEqual(len(submission.values.all()), 2)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 20)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'greg snider')

        # make sure removal case works
        new_vals = { 'age': 30 }
        self.xform.update_submission_from_dict(submission, new_vals)

        self.failUnlessEqual(len(submission.values.all()), 1)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 30)


