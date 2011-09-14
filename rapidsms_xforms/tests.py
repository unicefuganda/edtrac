"""
Basic tests for XForms
"""

import os
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.test.client import Client
from django.core.exceptions import ValidationError
from .models import XForm, XFormField, XFormFieldConstraint, xform_received
from eav.models import Attribute
from django.contrib.sites.models import Site
from .app import App
from rapidsms.messages.incoming import IncomingMessage
from rapidsms.models import Connection, Backend
from django.conf import settings

class ModelTest(TestCase): #pragma: no cover

    def setUp(self):
        self.user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
        self.user.save()

        self.xform = XForm.on_site.create(name='test', keyword='test', owner=self.user, 
                                          site=Site.objects.get_current(),
                                          response='thanks')

    def failIfValid(self, constraint, value, type):
        try:
            constraint.validate(value, type, 'sms')
            self.fail("Should have failed validating: %s" % value)
        except ValidationError:
            pass

    def failUnlessValid(self, constraint, value, type):
        try:
            constraint.validate(value, type, 'sms')
        except ValidationError:
            self.fail("Should have passed validating: %s" % value)

    def failIfClean(self, field, value, type):
        try:
            field.clean_submission(value, 'sms')
            self.fail("Should have failed cleaning: %s" % value)
        except ValidationError:
            pass

    def failUnlessClean(self, field, value, type):
        try:
            field.clean_submission(value, 'sms')
        except ValidationError:
            self.fail("Should have passed cleaning: %s" % value)

    def testMinValConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='min_val', test='10', message=msg)

        self.failIfValid(c, '1', XFormField.TYPE_INT)
        self.failUnlessValid(c, None, XFormField.TYPE_INT)
        self.failUnlessValid(c, '10', XFormField.TYPE_INT)
        self.failUnlessValid(c, '11', XFormField.TYPE_INT)

    def testMaxValConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='max_val', test='10', message=msg)

        self.failUnlessValid(c, '1', XFormField.TYPE_INT)
        self.failUnlessValid(c, '10', XFormField.TYPE_INT)
        self.failUnlessValid(c, None, XFormField.TYPE_INT)
        self.failIfValid(c, '11', XFormField.TYPE_INT)

    def testMinLenConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='min_len', test='2', message=msg)

        self.failIfValid(c, 'a', XFormField.TYPE_TEXT)
        self.failIfValid(c, '', XFormField.TYPE_TEXT)
        self.failUnlessValid(c, None, XFormField.TYPE_TEXT)
        self.failUnlessValid(c, 'ab', XFormField.TYPE_TEXT)
        self.failUnlessValid(c, 'abcdef', XFormField.TYPE_TEXT)

    def testMaxLenConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='max_len', test='3', message=msg)

        self.failUnlessValid(c, 'a', XFormField.TYPE_TEXT)
        self.failUnlessValid(c, '', XFormField.TYPE_TEXT)
        self.failUnlessValid(c, None, XFormField.TYPE_TEXT)
        self.failUnlessValid(c, 'abc', XFormField.TYPE_TEXT)
        self.failIfValid(c, 'abcdef', XFormField.TYPE_TEXT)

    def testReqValConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='req_val', message=msg)

        self.failUnlessValid(c, 'a', XFormField.TYPE_TEXT)
        self.failUnlessValid(c, 0, XFormField.TYPE_INT)
        self.failUnlessValid(c, '1.20', XFormField.TYPE_FLOAT)
        self.failIfValid(c, '', XFormField.TYPE_TEXT)
        self.failIfValid(c, None, XFormField.TYPE_TEXT)

    def testRegexConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='regex', test='^(mal|fev)$', message=msg)

        self.failIfValid(c, 'a', XFormField.TYPE_TEXT)
        self.failIfValid(c, '', XFormField.TYPE_TEXT)
        self.failIfValid(c, 'malo', XFormField.TYPE_TEXT)
        self.failUnlessValid(c, None, XFormField.TYPE_TEXT)
        self.failUnlessValid(c, 'MAL', XFormField.TYPE_TEXT)
        self.failUnlessValid(c, 'FeV', XFormField.TYPE_TEXT)

    def testIntField(self):
        field = self.xform.fields.create(field_type=XFormField.TYPE_INT, name='number', command='number')

        self.failUnlessClean(field, '1 ', XFormField.TYPE_INT)
        self.failUnlessClean(field, None, XFormField.TYPE_TEXT)
        self.failUnlessClean(field, '', XFormField.TYPE_TEXT)
        self.failIfClean(field, 'abc', XFormField.TYPE_TEXT)
        self.failIfClean(field, '1.34', XFormField.TYPE_FLOAT)

    def testDecField(self):
        field = self.xform.fields.create(field_type=XFormField.TYPE_FLOAT, name='number', command='number')

        self.failUnlessClean(field, '1', XFormField.TYPE_INT)
        self.failUnlessClean(field, ' 1.1', XFormField.TYPE_FLOAT)
        self.failUnlessClean(field, None, XFormField.TYPE_TEXT)
        self.failUnlessClean(field, '', XFormField.TYPE_TEXT)
        self.failIfClean(field, 'abc', XFormField.TYPE_TEXT)

    def testStrField(self):
        field = self.xform.fields.create(field_type=XFormField.TYPE_TEXT, name='string', command='string')

        self.failUnlessClean(field, '1', XFormField.TYPE_INT)
        self.failUnlessClean(field, '1.1', XFormField.TYPE_FLOAT)
        self.failUnlessClean(field, 'abc', XFormField.TYPE_TEXT)
        self.failUnlessClean(field, None, XFormField.TYPE_TEXT)
        self.failUnlessClean(field, '', XFormField.TYPE_TEXT)

    def testGPSField(self):
        field = self.xform.fields.create(field_type=XFormField.TYPE_GEOPOINT, name='location', command='location')

        self.failUnlessClean(field, '1 2', XFormField.TYPE_GEOPOINT)
        self.failUnlessClean(field, '1.1 1', XFormField.TYPE_GEOPOINT)
        self.failUnlessClean(field, '-1.1 -1.123', XFormField.TYPE_GEOPOINT)
        self.failUnlessClean(field, '', XFormField.TYPE_GEOPOINT)
        self.failUnlessClean(field, None, XFormField.TYPE_GEOPOINT)

        self.failIfClean(field, '1.123', XFormField.TYPE_GEOPOINT)
        self.failIfClean(field, '1.123 asdf', XFormField.TYPE_GEOPOINT)
        self.failIfClean(field, 'asdf', XFormField.TYPE_GEOPOINT)
        self.failIfClean(field, '-91.1 -1.123', XFormField.TYPE_GEOPOINT)
        self.failIfClean(field, '92.1 -1.123', XFormField.TYPE_GEOPOINT)
        self.failIfClean(field, '-1.1 -181.123', XFormField.TYPE_GEOPOINT)
        self.failIfClean(field, '2.1 181.123', XFormField.TYPE_GEOPOINT)

    def testFieldConstraints(self):
        field = self.xform.fields.create(field_type=XFormField.TYPE_TEXT, name='number', command='number')

        # test that with no constraings, all values work
        self.failUnlessClean(field, '1', XFormField.TYPE_TEXT)
        self.failUnlessClean(field, None, XFormField.TYPE_TEXT)
        self.failUnlessClean(field, 'abc', XFormField.TYPE_TEXT)

        # now add some constraints
        msg1 = 'error message'
        field.constraints.create(type='min_val', test='10', message=msg1)
        
        self.failIfClean(field, '1', XFormField.TYPE_TEXT)
        self.failIfClean(field, '-1', XFormField.TYPE_TEXT)
        self.failUnlessClean(field, '10', XFormField.TYPE_TEXT)

        # add another constraint
        msg2 = 'error message 2'
        field.constraints.create(type='max_val', test='50', message=msg2)
        self.failIfClean(field, '1', XFormField.TYPE_TEXT)
        self.failUnlessClean(field, '10', XFormField.TYPE_TEXT)
        self.failIfClean(field, '100', XFormField.TYPE_TEXT)

        # another, but set its order to be first
        msg3 = 'error message 3'
        field.constraints.create(type='min_val', test='5', message=msg3, order=0)
        self.failIfClean(field, '1', XFormField.TYPE_TEXT)
        self.failIfClean(field, '6', XFormField.TYPE_TEXT)

class SubmissionTest(TestCase): #pragma: no cover
    
    def setUp(self):
        # bootstrap a form
        self.user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
        self.user.save()

        self.xform = XForm.on_site.create(name='test', keyword='survey', owner=self.user,
                                          site=Site.objects.get_current(), response='thanks')

        self.gender_field = self.xform.fields.create(field_type=XFormField.TYPE_TEXT, name='gender', command='gender', order=1)
        self.gender_field.constraints.create(type='req_val', test='None', message="You must include a gender")
        self.field = self.xform.fields.create(field_type=XFormField.TYPE_INT, name='age', command='age', order=2)
        self.field.constraints.create(type='req_val', test='None', message="You must include an age")
        self.name_field = self.xform.fields.create(field_type=XFormField.TYPE_TEXT, name='name', command='name', order=4)

    def testDataTypes(self):
        field = self.xform.fields.create(field_type=XFormField.TYPE_TEXT, name='field', command='field', order=1)
        self.failUnlessEqual(field.datatype, 'text')
        field.field_type=XFormField.TYPE_INT
        field.save()
        self.failUnlessEqual(field.datatype, 'int')

    def testOrdering(self):
        # submit a record, some errors only occur after there is at least one
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey +age 10 +name matt berg +gender male"))

        fields = self.xform.fields.all()
        self.failUnlessEqual(self.gender_field.pk, fields[0].pk)
        self.failUnlessEqual(self.field.pk, fields[1].pk)
        self.failUnlessEqual(self.name_field.pk, fields[2].pk)

        # move gender to the back
        self.gender_field.order = 10
        self.gender_field.save()

        fields = self.xform.fields.all()
        self.failUnlessEqual(self.field.pk, fields[0].pk)
        self.failUnlessEqual(self.name_field.pk, fields[1].pk)
        self.failUnlessEqual(self.gender_field.pk, fields[2].pk)

    def testSlugs(self):
        field = self.xform.fields.create(field_type=XFormField.TYPE_TEXT, name='field', command='foo', order=1)
        self.failUnlessEqual(field.slug, 'survey_foo')
        field.command = 'bar'
        field.save()
        self.failUnlessEqual(field.slug, 'survey_bar')

        # rename our form
        self.xform.keyword = 'roger'
        self.xform.save()

        field = XFormField.on_site.get(pk=field)
        self.failUnlessEqual(field.slug, 'roger_bar')

    def testSMSSubmission(self):
        self.assertEquals('thanks', self.xform.response)

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey +age 10 +name matt berg +gender male"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        # make sure case doesn't matter
        submission = self.xform.process_sms_submission(IncomingMessage(None, "Survey +age 10 +name matt berg +gender male"))
        self.failUnlessEqual(submission.has_errors, False)

        # make sure it works with space in front of keyword
        submission = self.xform.process_sms_submission(IncomingMessage(None, "  survey male 10 +name matt berg"))
        self.failUnlessEqual(submission.has_errors, False)

        # test with just an age and gender
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 2)
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)

        # mix of required and not
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10 +name matt berg"))
        self.failUnlessEqual('thanks', submission.response)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        # make sure optional works as well 
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10 matt"))
        self.failUnlessEqual('thanks', submission.response)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        # make sure we record errors if there is a missing age
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey +name luke skywalker"))
        self.failUnlessEqual(submission.has_errors, True)

        # our response should be an error message
        self.failIfEqual('thanks', submission.response)
        self.failUnlessEqual(2, len(submission.errors))

        # make sure we record errors if there is just the keyword
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey"))
        self.failUnlessEqual(submission.has_errors, True)
        self.failUnlessEqual(2, len(submission.errors))

    def testSingleFieldSpecialCase(self):
        special_xform = XForm.on_site.create(name='test special', keyword='reg', owner=self.user, separator=',',
                                          site=Site.objects.get_current(), response='thanks')        
        field = special_xform.fields.create(field_type=XFormField.TYPE_TEXT, name='name', command='name')
        submission = special_xform.process_sms_submission(IncomingMessage(None, "+reg davey crockett"))
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'davey crockett')

    def testSignal(self):
        # add a listener to our signal
        class Listener:
            def handle_submission(self, sender, **args):
                if args['xform'].keyword == 'survey':
                    self.submission = args['submission']
                    self.xform = args['xform']


        listener = Listener()
        xform_received.connect(listener.handle_submission)

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10 +name matt berg"))
        self.failUnlessEqual(listener.submission, submission)
        self.failUnlessEqual(listener.xform, self.xform)

        # test that it works via update as well
        new_vals = { 'age': 20, 'name': 'greg snider' }
        self.xform.update_submission_from_dict(submission, new_vals)

        self.failUnlessEqual(listener.submission.values.get(attribute__name='age').value, 20)
        self.failUnlessEqual(listener.submission.values.get(attribute__name='name').value, 'greg snider')

    def testUpdateFromDict(self):
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male +age 10 +name matt berg"))
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


    def testCustomField(self):
        # register Users as being an XForm field
        def lookup_user(command, username):
            return User.objects.get(username=username)

        XFormField.register_field_type('user', 'User', lookup_user, 
                               xforms_type='string', db_type=XFormField.TYPE_OBJECT)

        # add a user field to our xform
        field = self.xform.fields.create(field_type='user', name='user', command='user', order=3)
        field.constraints.create(type='req_val', test='None', message="You must include a user")

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10 fred"))

        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='user').value, self.user)

    def testConfirmationId(self):
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10"))
        self.assertEquals(1, submission.confirmation_id)

        # and another
        submission2 = self.xform.process_sms_submission(IncomingMessage(None, "survey male 12"))
        self.assertEquals(2, submission2.confirmation_id)

        self.xform2 = XForm.on_site.create(name='test2', keyword='test2', owner=self.user,
                                           site=Site.objects.get_current())

        submission3 = self.xform2.process_sms_submission(IncomingMessage(None, "test2"))
        self.assertEquals(1, submission3.confirmation_id)

        submission4 = self.xform.process_sms_submission(IncomingMessage(None, "survey male 21"))
        self.assertEquals(3, submission4.confirmation_id)

        # that resaving the submission doesn't increment our id
        submission5 = self.xform.process_sms_submission(IncomingMessage(None, "survey male 22"))
        self.assertEquals(4, submission5.confirmation_id)
        submission5.raw = "foo"
        submission5.save()
        self.assertEquals(4, submission5.confirmation_id)

        submission6 = self.xform.process_sms_submission(IncomingMessage(None, "survey male 23"))
        self.assertEquals(5, submission6.confirmation_id)

    def testTemplateResponse(self):
        # codify the confirmation id
        self.xform.response = 'Your confirmation id is: {{ confirmation_id|codify:"SA" }}'
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10"))

        # should be safe to use a static value since we are the first test
        self.failUnlessEqual(submission.response, "Your confirmation id is: SA0001")

        # no prefix
        self.xform.response = 'Your confirmation id is: {{ confirmation_id|codify }}'
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10"))

        # should be safe to use a static value since we are the first test
        self.failUnlessEqual(submission.response, "Your confirmation id is: 0002")

        # now test no template
        self.xform.response = "Thanks for sending your message"
        self.xform.save()

        # assert the message response is right
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10"))
        self.failUnlessEqual(submission.response, self.xform.response)

        # now change the xform to return the age and gender
        self.xform.response = "You recorded an age of {{ age }} and a gender of {{ gender }}.  Your confirmation id is {{ confirmation_id }}."
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10"))
        self.failUnlessEqual(submission.response, "You recorded an age of 10 and a gender of male.  Your confirmation id is 4.")

        # if they insert a command that isn't there, it should just be empty
        self.xform.response = "You recorded an age of {{ age }} and a gender of {{ gender }}.  {{ not_there }} Thanks."
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10"))
        self.failUnlessEqual(submission.response, "You recorded an age of 10 and a gender of male.   Thanks.")

        # make sure template arguments work
        self.xform.response = "The two values together are: {{ age|add:gender }}."
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10"))
        self.failUnlessEqual(submission.response, "The two values together are: 10.")

        # assert we don't let forms save with templates that fail
        self.xform.response = "You recorded an age of {{ bad template }}"
        try:
            self.xform.save()
            self.fail("Should have failed in save.")
        except Exception as e:
            # expected exception because the template is bad, let it pass
            pass

    def testCommandPrefixes(self):
        # set the prefix to '-' instead of '+'
        self.xform.command_prefix = '-'
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey -age 10 -name matt berg -gender male"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        # test duplicating the prefix or having junk in it
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey -age 10 --name matt berg -+gender male"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        # set the prefix to nothing instead of '+'
        self.xform.command_prefix = None
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey age 10 name matt berg gender male"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        # test mix of required and not required
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10 name matt berg"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

    def testSeparators(self):
        self.xform.separator = None
        self.xform.save()

        # this is also testing an edge case of a value being 0
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 0 matt"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 0)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        self.xform.separator = ","
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey,male,10,matt berg"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male, 10, matt berg"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male,10,matt berg"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male, , 10,,, matt berg"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male,10, +name bniz berg"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'bniz berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male,10 +name bniz berg"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'bniz berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male,10,, +name bniz berg"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'bniz berg')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

    def testCustomKeywordPrefix(self):
        self.xform.keyword_prefix = '+'
        
        submission = self.xform.process_sms_submission(IncomingMessage(None, " +survey male 10 matt"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        submission = self.xform.process_sms_submission(IncomingMessage(None, " + survey male 10 matt"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

        submission = self.xform.process_sms_submission(IncomingMessage(None, " ++ survey male 10 matt"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

    def testCustomResponse(self):
        # add a listener to our signal to change what our response will be
        class Listener:
            def handle_submission(self, sender, **args):
                if args['xform'].keyword == 'survey':
                    self.submission = args['submission']
                    self.xform = args['xform']

                    # make sure our template variables are set on the submission
                    template_vars = self.submission.template_vars

                    # set our response to 'hello world' instead of 'thanks'
                    self.submission.response = XForm.render_response("hello world {{ age }}", template_vars)


        listener = Listener()
        xform_received.connect(listener.handle_submission)

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10 +name matt berg"))
        self.failUnlessEqual(listener.submission, submission)
        self.failUnlessEqual(listener.xform, self.xform)
        self.failUnlessEqual("hello world 10", submission.response)

        # test that it works via update as well
        new_vals = { 'age': 20, 'name': 'greg snider' }
        self.xform.update_submission_from_dict(submission, new_vals)
        
        self.failUnlessEqual(listener.submission.values.get(attribute__name='age').value, 20)
        self.failUnlessEqual(listener.submission.values.get(attribute__name='name').value, 'greg snider')

    def testFindForm(self):
        """
        Tests how we find which form a particular message matches.
        """

        # test simple case
        self.assertEquals(self.xform, XForm.find_form("survey"))
        self.assertEquals(None, XForm.find_form("missing"))

        # have another form that is similar, to test that we match correctly in exact matches
        surve_form = XForm.on_site.create(name='surve', keyword='surve', owner=self.user,
                                          site=Site.objects.get_current(), response='thanks')
        
        self.assertEquals(self.xform, XForm.find_form("survey hello world"))
        self.assertFalse(XForm.find_form("foobar hello world"))

        # make sure we match existing forms exactly
        self.assertEquals(surve_form, XForm.find_form("surve hello world"))
        
        self.assertFalse(XForm.find_form("survy hello world"))
        self.assertFalse(XForm.find_form("survye hello world"))
        self.assertEquals(self.xform, XForm.find_form("0survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("  survey hello world"))
        self.assertEquals(self.xform, XForm.find_form(".survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("furvey hello world"))
        self.assertEquals(self.xform, XForm.find_form("..survey hello world"))
        self.assertEquals(self.xform, XForm.find_form(".+survey hello world"))

        # quotes
        self.assertEquals(self.xform, XForm.find_form("'survey' hello world"))
        self.assertEquals(self.xform, XForm.find_form("'survey', hello world"))
        self.assertEquals(self.xform, XForm.find_form("survey,hello world"))

        # shouldn't pass, edit distance of 2
        self.assertEquals(None, XForm.find_form("furvey1 hello world"))

        surve_form.delete()

        # wrong keyword
        self.assertFalse(XForm.find_form("foobar hello world"))

        # fuzzy match tests when only one form exists
        self.assertEquals(self.xform, XForm.find_form("surve hello world"))
        self.assertEquals(self.xform, XForm.find_form("survy hello world"))
        self.assertEquals(self.xform, XForm.find_form("survye hello world"))
        self.assertEquals(self.xform, XForm.find_form("0survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("  survey hello world"))
        self.assertEquals(self.xform, XForm.find_form(".survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("furvey hello world"))
        self.assertEquals(self.xform, XForm.find_form("..survey hello world"))
        self.assertEquals(self.xform, XForm.find_form(".+survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("+survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("-+-survey hello world"))

        # shouldn't pass, edit distance of 2
        self.assertFalse(XForm.find_form("furvey1 hello world"))
        self.assertFalse(XForm.find_form("10 + 20 +survey hello world"))
        self.assertFalse(XForm.find_form("my survey hello world"))

        # test when we have a keyword prefix
        self.xform.keyword_prefix = '+'
        self.xform.save()

        # no prefix, no match
        self.assertFalse(XForm.find_form("survey hello world"))

        # wrong keyword
        self.assertFalse(XForm.find_form("foobar hello world"))

        # fuzzy match tests when only one form exists
        self.assertEquals(self.xform, XForm.find_form("+surve hello world"))
        self.assertEquals(self.xform, XForm.find_form("+survy hello world"))
        self.assertEquals(self.xform, XForm.find_form("+survye hello world"))
        self.assertEquals(self.xform, XForm.find_form("+0survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("+  survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("+.survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("+furvey hello world"))
        self.assertEquals(self.xform, XForm.find_form("+..survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("+.+survey hello world"))
        self.assertEquals(self.xform, XForm.find_form(".+survey hello world"))
        self.assertEquals(self.xform, XForm.find_form("--+-survey hello world"))

        # shouldn't pass, edit distance of 2
        self.assertFalse(XForm.find_form("+furvey1 hello world"))
        self.assertFalse(XForm.find_form("10 + 20 +survey hello world"))
        self.assertFalse(XForm.find_form("my survey hello world"))


    def testApp(self):
        """
        Tests that our main app.py handles messages correctly.  More detailed testing is done at a unit
        level, this just makes sure that the main routing works.
        """
        
        xforms_app = App(None)

        msg = IncomingMessage(None, "survey male 10 matt")
        self.assertTrue(xforms_app.handle(msg))
        self.assertEquals(1, len(self.xform.submissions.all()))

        msg = IncomingMessage(None, "foo male 10 matt")
        self.assertFalse(xforms_app.handle(msg))
        self.assertEquals(1, len(self.xform.submissions.all()))

    def testEpi(self):
        
        #+epi ma 12, bd 5

        xform = XForm.on_site.create(name='epi_test', keyword='epi', owner=self.user, command_prefix=None, 
                                     keyword_prefix = '+', separator = ',',
                                     site=Site.objects.get_current(), response='thanks')

        f1 = xform.fields.create(field_type=XFormField.TYPE_INT, name='ma', command='ma', order=0)        
        f2 = xform.fields.create(field_type=XFormField.TYPE_INT, name='bd', command='bd', order=1)

        submission = xform.process_sms_submission(IncomingMessage(None, "+epi ma 12, bd 5"))
        
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 2)
        self.failUnlessEqual(submission.values.get(attribute__name='ma').value, 12)
        self.failUnlessEqual(submission.values.get(attribute__name='bd').value, 5)

        # missing value
        submission = xform.process_sms_submission(IncomingMessage(None, "+epi ma"))
        self.failUnless(submission.has_errors)

        # duplicate values
        submission = xform.process_sms_submission(IncomingMessage(None, "+epi ma 12, ma 5"))
        self.failUnless(submission.has_errors)

        #+muac davey crockett, m, 6 months, red

        xform = XForm.on_site.create(name='muac_test', keyword='muac', owner=self.user, command_prefix=None, 
                                     keyword_prefix = '+', separator = ',',
                                     site=Site.objects.get_current(), response='thanks')

        f1 = xform.fields.create(field_type=XFormField.TYPE_TEXT, name='name', command='name', order=0)     
        f1.constraints.create(type='req_val', test='None', message="You must include a name")
        f2 = xform.fields.create(field_type=XFormField.TYPE_TEXT, name='gender', command='gender', order=1)
        f2.constraints.create(type='req_val', test='None', message="You must include a gender")
        f3 = xform.fields.create(field_type=XFormField.TYPE_TEXT, name='age', command='age', order=2)
        f3.constraints.create(type='req_val', test='None', message="You must include an age")
        f4 = xform.fields.create(field_type=XFormField.TYPE_TEXT, name='length', command='length', order=3)
        f4.constraints.create(type='req_val', test='None', message="You must include a length")

        submission = xform.process_sms_submission(IncomingMessage(None, "+muac davey crockett, m, 6 months, red"))
        
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 4)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, "davey crockett")
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, "m")
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, "6 months")
        self.failUnlessEqual(submission.values.get(attribute__name='length').value, "red")

        #+death malthe borg, m, 5day

        xform = XForm.on_site.create(name='death_test', keyword='death', owner=self.user, command_prefix=None, 
                                     keyword_prefix = '+', separator = ',',
                                     site=Site.objects.get_current(), response='thanks')

        f1 = xform.fields.create(field_type=XFormField.TYPE_TEXT, name='name', command='name', order=0)        
        f2 = xform.fields.create(field_type=XFormField.TYPE_TEXT, name='gender', command='gender', order=1)
        f3 = xform.fields.create(field_type=XFormField.TYPE_TEXT, name='age', command='age', order=2)

        submission = xform.process_sms_submission(IncomingMessage(None, "+death malthe borg, m, 5day"))
        self.assertEquals(xform, XForm.find_form("+derth malthe borg, m, 5day"))
        self.assertEquals(xform, XForm.find_form("+daeth malthe borg, m, 5day"))        
        
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, "malthe borg")
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, "m")
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, "5day")


    def testPullerCustomerField(self):
        # Tests creating a field that is based on the connection of the message, not anything in the message
        # itself.

        def parse_connection(command, value):
            # we should be able to find a connection with this identity
            matches = Connection.objects.filter(identity=value)
            if matches:
                return matches[0]

            raise ValidationError("%s parameter value of '%s' does not match any connections.")

        def pull_connection(command, message):
            # this pulls the actual hone number from the message and returns it as a string
            # note that in this case we will actually only match if the phone number starts with '072'
            identity = message.connection.identity
            if identity.startswith('072'):
                return identity
            else:
                return None

        XFormField.register_field_type('conn', 'Connection', parse_connection,
                                       xforms_type='string', db_type=XFormField.TYPE_OBJECT, puller=pull_connection)
        

        # create a new form
        xform = XForm.on_site.create(name='sales', keyword='sales', owner=self.user,
                                     site=Site.objects.get_current(), response='thanks for submitting your report')

        # create a single field for our connection puller
        f1 = xform.fields.create(field_type='conn', name='conn', command='conn', order=0)
        f1.constraints.create(type='req_val', test='None', message="Missing connection.")

        f2 = xform.fields.create(field_type=XFormField.TYPE_INT, name='age', command='age', order=2)        

        # create some connections to work with
        butt = Backend.objects.create(name='foo')
        conn1 = Connection.objects.create(identity='0721234567', backend=butt)
        conn2 = Connection.objects.create(identity='0781234567', backend=butt)

        # check that we parse out the connection correctly
        submission = xform.process_sms_submission(IncomingMessage(conn1, "sales 123"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 2)
        self.failUnlessEqual(submission.values.get(attribute__name='conn').value, conn1)
        self.failUnlessEqual(123, submission.eav.sales_age)

        # now try with a connection that shouldn't match
        submission = xform.process_sms_submission(IncomingMessage(conn2, "sales"))
        self.failUnlessEqual(submission.has_errors, True)
        self.failUnlessEqual(len(submission.values.all()), 0)

    def testAgeCustomField(self):
        # creates a new field type that parses strings into an integer number of days
        # ie, given a string like '5days' or '6 months' will return either 5, or 30

        import re

        # register a time parser
        def parse_timespan(command, value):
            match = re.match("(\d+)\W*months?", value, re.IGNORECASE)
            if match:
                return int(match.group(1))*30
            match = re.match("(\d+)\W*days?", value, re.IGNORECASE)
            if match:
                return int(match.group(1))

            raise ValidationError("%s parameter value of '%s' is not a valid timespan." % (command, value))

        XFormField.register_field_type('timespan', 'Timespan', parse_timespan, 
                                       xforms_type='string', db_type=XFormField.TYPE_INT)

        # create a new form
        xform = XForm.on_site.create(name='time', keyword='time', owner=self.user,
                                     site=Site.objects.get_current(), response='thanks')

        f1 = xform.fields.create(field_type='timespan', name='timespan', command='timespan', order=0)        

        # try five months
        submission = xform.process_sms_submission(IncomingMessage(None, "time +timespan 5 months"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 1)
        self.failUnlessEqual(submission.values.get(attribute__name='timespan').value, 150)

        # try 6 days
        submission = xform.process_sms_submission(IncomingMessage(None, "time +timespan 6days"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 1)
        self.failUnlessEqual(submission.values.get(attribute__name='timespan').value, 6)

        # something invalid
        submission = xform.process_sms_submission(IncomingMessage(None, "time +timespan infinity plus one"))
        self.failUnlessEqual(submission.has_errors, True)

    def testImportSubmissions(self):

        # our fake submitter
        backend, created = Backend.objects.get_or_create(name='test')
        connection, created = Connection.objects.get_or_create(identity='123', backend=backend)
        
        # Our form has fields: gender, age, and name (optional)
        # try passing a string for an int field
        values = { 'gender': 'male', 'age': 'Should be number', 'name': 'Eugene'}
        self.assertRaises(ValidationError, self.xform.process_import_submission, "", connection, values)
        self.assertEquals(0, len(self.xform.submissions.all()))

        # try sending something that is not a string
        values = { 'age': 25, 'gender': 'male', 'name': 'Eugene'}
        self.assertRaises(TypeError, self.xform.process_import_submission, "", connection, values)
        self.assertEquals(0, len(self.xform.submissions.all()))

        # try excluding an optional field
        values = { 'age': '25', 'gender': 'male'}
        self.xform.process_import_submission("", connection, values)
        self.assertEquals(1, len(self.xform.submissions.all()))

        # try excluding a required field
        values = { 'gender': 'male', 'name': 'Eugene'}
        self.assertRaises(ValidationError, self.xform.process_import_submission, "", connection, values)
        self.assertEquals(1, len(self.xform.submissions.all()))
        
        # check that constraint is upheld
        self.field.constraints.create(type='max_val', test='100', message="Nobody is that old")
        self.field.constraints.create(type='min_val', test='0', message="You are negative old")

        values = { 'gender': 'male', 'age': '900', 'name': 'Eugene'}
        self.assertRaises(ValidationError, self.xform.process_import_submission, "", connection, values)
        self.assertEquals(1, len(self.xform.submissions.all()))

        values = { 'gender': 'male', 'age': '-1', 'name': 'Eugene'}
        self.assertRaises(ValidationError, self.xform.process_import_submission, "", connection, values)
        self.assertEquals(1, len(self.xform.submissions.all()))

        # try sending extra fields that are not in the form
        values = { 'gender': 'male', 'age': 'Should be number', 'name': 'Eugene', 'extra': "This shouldn't be provided"}
        self.assertRaises(ValidationError, self.xform.process_import_submission, "", connection, values)
        self.assertEquals(1, len(self.xform.submissions.all()))

        # try sending extra fields that are not in the form
        values = { 'gender': 'male', 'age': '99', 'name': 'Eugene'}
        self.xform.process_import_submission("", connection, values)
        self.assertEquals(2, len(self.xform.submissions.all()))

    def testMultimediaOptionalOnSMS(self):
        xform = XForm.on_site.create(name='image', keyword='image', owner=self.user, command_prefix='+', 
                                     site=Site.objects.get_current(), response='thanks')

        f1 = xform.fields.create(field_type=XFormField.TYPE_TEXT, name='name', command='name', order=0)
        f2 = xform.fields.create(field_type=XFormField.TYPE_IMAGE, name='image', command='image', order=1)
        f3 = xform.fields.create(field_type=XFormField.TYPE_AUDIO, name='audio', command='audio', order=2)
        f4 = xform.fields.create(field_type=XFormField.TYPE_VIDEO, name='video', command='video', order=3)        

        # make the photo field required, though this will only really kick in during SMS submission
        f2.constraints.create(type='req_val', test='None', message="You must include an image")
        f3.constraints.create(type='req_val', test='None', message="You must include audio")
        f4.constraints.create(type='req_val', test='None', message="You must include a video")        

        submission = xform.process_sms_submission(IncomingMessage(None, "image +name Michael Jackson"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 1)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, "Michael Jackson")


    def testODKDefinition(self):
        xform = XForm.on_site.create(name='multimedia', keyword='multimedia', owner=self.user, command_prefix='+', 
                                     site=Site.objects.get_current(), response='thanks')

        f1 = xform.fields.create(field_type=XFormField.TYPE_TEXT, name='name', command='name', order=0)
        f2 = xform.fields.create(field_type=XFormField.TYPE_IMAGE, name='image', command='image', order=1)
        f3 = xform.fields.create(field_type=XFormField.TYPE_AUDIO, name='audio', command='audio', order=2)
        f4 = xform.fields.create(field_type=XFormField.TYPE_VIDEO, name='video', command='video', order=3)

        c = Client()
        response = c.get("/xforms/odk/get/%d/" % xform.id)
        self.assertEquals(200, response.status_code)

        from xml.dom.minidom import parseString
        xml = parseString(response.content)

        body = xml.getElementsByTagName("h:body")[0]

        inputs = body.getElementsByTagName("input")
        self.assertEquals(1, len(inputs))
        self.assertEquals("name", inputs[0].getAttribute("ref"))

        uploads = body.getElementsByTagName("upload")
        self.assertEquals(3, len(uploads))
        self.assertEquals("image", uploads[0].getAttribute("ref"))
        self.assertEquals("image/*", uploads[0].getAttribute("mediatype"))

        self.assertEquals("audio", uploads[1].getAttribute("ref"))
        self.assertEquals("audio/*", uploads[1].getAttribute("mediatype"))

        self.assertEquals("video", uploads[2].getAttribute("ref"))
        self.assertEquals("video/*", uploads[2].getAttribute("mediatype"))

    def testODKSubmission(self):
        xform = XForm.on_site.create(name='multimedia', keyword='multimedia', owner=self.user, command_prefix='+', 
                                     site=Site.objects.get_current(), response='thanks')

        f1 = xform.fields.create(field_type=XFormField.TYPE_TEXT, name='name', command='name', order=0)
        f2 = xform.fields.create(field_type=XFormField.TYPE_IMAGE, name='image', command='image', order=1)
        f3 = xform.fields.create(field_type=XFormField.TYPE_AUDIO, name='audio', command='audio', order=2)
        f4 = xform.fields.create(field_type=XFormField.TYPE_VIDEO, name='video', command='video', order=3)        

        xml = "<?xml version='1.0' ?><data><image>test__image.jpg</image>"
        "<audio>test__audio.jpg</audio><video>test__video.jpg</video><name>Michael Jackson</name></data>"

        # build up our dict of xml values and binaries
        binaries = dict()
        values = dict()

        values['name'] = "Michael Jackson"
        values['image'] = "test__image.jpg"
        values['audio'] = "test__audio.mp3"
        values['video'] = "test__video.mp4"        
        
        binaries['test__image.jpg'] = "jpgimage"
        binaries['test__audio.mp3'] = "mp3file"
        binaries['test__video.mp4'] = "vidfile"

        # remove those files if they exist
        directory = os.path.join(settings.MEDIA_ROOT, 'binary')
        for name in ['test__image.jpg', 'test__audio.mp3', 'test__video.mp4']:
            try:
                os.remove(os.path.join(directory, name))
            except:
                pass

        submission = xform.process_odk_submission(xml, values, binaries)

        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 4)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, "Michael Jackson")

        binary = submission.values.get(attribute__name='image').value.binary
        self.failUnlessEqual("binary/test__image.jpg", binary.name)
        self.failUnlessEqual("jpgimage", binary.read())

        binary = submission.values.get(attribute__name='audio').value.binary
        self.failUnlessEqual("binary/test__audio.mp3", binary.name)        
        self.failUnlessEqual("mp3file", binary.read())

        binary = submission.values.get(attribute__name='video').value.binary
        self.failUnlessEqual("binary/test__video.mp4", binary.name)
        self.failUnlessEqual("vidfile", binary.read())        
        

        
          
