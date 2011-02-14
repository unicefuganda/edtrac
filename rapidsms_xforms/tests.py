"""
Basic tests for XForms
"""

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

class ModelTest(TestCase): #pragma: no cover

    def setUp(self):
        self.user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
        self.user.save()

        self.xform = XForm.on_site.create(name='test', keyword='test', owner=self.user, 
                                          site=Site.objects.get_current(),
                                          response='thanks')

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
        self.failUnlessValid(c, 0)
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
        field = self.xform.fields.create(field_type=XFormField.TYPE_INT, name='number', command='number')

        self.failUnlessClean(field, '1 ')
        self.failUnlessClean(field, None)
        self.failUnlessClean(field, '')
        self.failIfClean(field, 'abc')
        self.failIfClean(field, '1.34')

    def testDecField(self):
        field = self.xform.fields.create(field_type=XFormField.TYPE_FLOAT, name='number', command='number')

        self.failUnlessClean(field, '1')
        self.failUnlessClean(field, ' 1.1')
        self.failUnlessClean(field, None)
        self.failUnlessClean(field, '')
        self.failIfClean(field, 'abc')

    def testStrField(self):
        field = self.xform.fields.create(field_type=XFormField.TYPE_TEXT, name='string', command='string')

        self.failUnlessClean(field, '1')
        self.failUnlessClean(field, '1.1')
        self.failUnlessClean(field, 'abc')
        self.failUnlessClean(field, None)
        self.failUnlessClean(field, '')

    def testGPSField(self):
        field = self.xform.fields.create(field_type=XFormField.TYPE_GEOPOINT, name='location', command='location')

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
        field = self.xform.fields.create(field_type=XFormField.TYPE_TEXT, name='number', command='number')

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
        # first test no template
        self.xform.response = "Thanks for sending your message"
        self.xform.save()

        # assert the message response is right
        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10"))
        self.failUnlessEqual(submission.response, self.xform.response)

        # now change the xform to return the age and gender
        self.xform.response = "You recorded an age of {{ age }} and a gender of {{ gender }}.  Your confirmation id is {{ confirmation_id }}."
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10"))
        self.failUnlessEqual(submission.response, "You recorded an age of 10 and a gender of male.  Your confirmation id is 2.")

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
        self.xform.separator = ","
        self.xform.save()

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10 matt"))
        self.failUnlessEqual(submission.has_errors, False)
        self.failUnlessEqual(len(submission.values.all()), 3)
        self.failUnlessEqual(submission.values.get(attribute__name='age').value, 10)
        self.failUnlessEqual(submission.values.get(attribute__name='name').value, 'matt')
        self.failUnlessEqual(submission.values.get(attribute__name='gender').value, 'male')

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

                    # set our response to 'hello world' instead of 'thanks'
                    self.submission.response = "hello world"


        listener = Listener()
        xform_received.connect(listener.handle_submission)

        submission = self.xform.process_sms_submission(IncomingMessage(None, "survey male 10 +name matt berg"))
        self.failUnlessEqual(listener.submission, submission)
        self.failUnlessEqual(listener.xform, self.xform)
        self.failUnlessEqual("hello world", submission.response)

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
