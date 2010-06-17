"""
Basic tests for XForms
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.test.client import Client
from .models import XForm, XFormField, XFormFieldConstraint, xform_received

class ViewTest(TestCase): # pragma: no cover
    urls = 'xforms.urls'

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

    def testMinValConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='min_val', test='10', message=msg)

        self.failUnlessEqual(c.check_value('1'), msg)
        self.failUnlessEqual(c.check_value(None), None)
        self.failUnlessEqual(c.check_value('10'), None)
        self.failUnlessEqual(c.check_value('11'), None)

    def testMaxValConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='max_val', test='10', message=msg)

        self.failUnlessEqual(c.check_value('1'), None)
        self.failUnlessEqual(c.check_value('10'), None)
        self.failUnlessEqual(c.check_value(None), None)
        self.failUnlessEqual(c.check_value('11'), msg)

    def testMinLenConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='min_len', test='2', message=msg)

        self.failUnlessEqual(c.check_value('a'), msg)
        self.failUnlessEqual(c.check_value(''), msg)
        self.failUnlessEqual(c.check_value(None), None)
        self.failUnlessEqual(c.check_value('ab'), None)
        self.failUnlessEqual(c.check_value('abcdef'), None)

    def testMaxLenConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='max_len', test='3', message=msg)

        self.failUnlessEqual(c.check_value('a'), None)
        self.failUnlessEqual(c.check_value(''), None)
        self.failUnlessEqual(c.check_value(None), None)
        self.failUnlessEqual(c.check_value('ab'), None)
        self.failUnlessEqual(c.check_value('abc'), None)
        self.failUnlessEqual(c.check_value('abcdef'), msg)

    def testReqValConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='req_val', message=msg)

        self.failUnlessEqual(c.check_value('a'), None)
        self.failUnlessEqual(c.check_value('1.20'), None)
        self.failUnlessEqual(c.check_value(''), msg)
        self.failUnlessEqual(c.check_value(None), msg)

    def testRegexConstraint(self):
        msg = 'error message'
        c = XFormFieldConstraint(type='regex', test='^(mal|fev)$', message=msg)

        self.failUnlessEqual(c.check_value('a'), msg)
        self.failUnlessEqual(c.check_value(''), msg)
        self.failUnlessEqual(c.check_value('malo'), msg)
        self.failUnlessEqual(c.check_value(None), None)
        self.failUnlessEqual(c.check_value('MAL'), None)
        self.failUnlessEqual(c.check_value('FeV'), None)

    def testIntField(self):
        field = self.xform.fields.create(type='int', caption='number', command='number')

        self.failUnlessEqual(field.check_value('1 '), None)
        self.failUnlessEqual(field.check_value(None), None)
        self.failUnlessEqual(field.check_value(''), None)
        self.failIfEqual(field.check_value('abc'), None)
        self.failIfEqual(field.check_value('1.34'), None)

    def testDecField(self):
        field = self.xform.fields.create(type='dec', caption='number', command='number')

        self.failUnlessEqual(field.check_value('1'), None)
        self.failUnlessEqual(field.check_value(' 1.1'), None)
        self.failUnlessEqual(field.check_value(None), None)
        self.failUnlessEqual(field.check_value(''), None)
        self.failIfEqual(field.check_value('abc'), None)

    def testStrField(self):
        field = self.xform.fields.create(type='str', caption='string', command='string')

        self.failUnlessEqual(field.check_value('1'), None)
        self.failUnlessEqual(field.check_value('1.1'), None)
        self.failUnlessEqual(field.check_value('abc'), None)
        self.failUnlessEqual(field.check_value(''), None)
        self.failUnlessEqual(field.check_value(None), None)

    def testGPSField(self):
        field = self.xform.fields.create(type='gps', caption='location', command='location')

        self.failUnlessEqual(field.check_value('1 2'), None)
        self.failUnlessEqual(field.check_value('1.1 1'), None)
        self.failUnlessEqual(field.check_value('-1.1 -1.123'), None)
        self.failUnlessEqual(field.check_value(''), None)
        self.failUnlessEqual(field.check_value(None), None)

        self.failIfEqual(field.check_value('1.123'), None)
        self.failIfEqual(field.check_value('1.123 asdf'), None)
        self.failIfEqual(field.check_value('asdf'), None)
        self.failIfEqual(field.check_value('-91.1 -1.123'), None)
        self.failIfEqual(field.check_value('92.1 -1.123'), None)
        self.failIfEqual(field.check_value('-1.1 -181.123'), None)
        self.failIfEqual(field.check_value('2.1 181.123'), None)

    def testFieldConstraints(self):
        field = self.xform.fields.create(type='str', caption='number', command='number')

        # test that with no constraings, all values work
        self.failUnlessEqual(field.check_value('1'), None)
        self.failUnlessEqual(field.check_value(None), None)
        self.failUnlessEqual(field.check_value('abc'), None)

        # now add some constraints
        msg1 = 'error message'
        field.constraints.create(type='min_val', test='10', message=msg1)
        
        self.failUnlessEqual(field.check_value('1'), msg1)
        self.failUnlessEqual(field.check_value('10'), None)

        # add another constraint
        msg2 = 'error message 2'
        field.constraints.create(type='max_val', test='50', message=msg2)
        self.failUnlessEqual(field.check_value('1'), msg1)
        self.failUnlessEqual(field.check_value('10'), None)
        self.failUnlessEqual(field.check_value('100'), msg2)

        # another, but set its order to be first
        msg3 = 'error message 3'
        field.constraints.create(type='min_val', test='5', message=msg3, order=0)
        self.failUnlessEqual(field.check_value('1'), msg3)
        self.failUnlessEqual(field.check_value('6'), msg1)


class SubmisionTest(TestCase): #pragma: no cover
    
    def setUp(self):
        # bootstrap a form
        self.user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
        self.user.save()

        self.xform = XForm(name='test', keyword='survey', owner=self.user)
        self.xform.save()

        self.xform.fields.create(type='int', caption='age', command='age')
        self.xform.fields.create(type='str', caption='name', command='name')

    def testSMSSubmission(self):
        submission = self.xform.process_sms_submission("survey +age 10 +name matt berg", None)
        self.failUnlessEqual(len(submission.values.all()), 2)

    def testSignal(self):
        # add a listener to our signal
        class Listener:
            def handle_submission(self, sender, **args):
                if args['xform'].keyword == 'survey':
                    self.submission = args['submission']
                    self.xform = args['xform']


        listener = Listener()
        xform_received.connect(listener.handle_submission)

        submission = self.xform.process_sms_submission("survey +age 10 +name matt berg", None)
        self.failUnlessEqual(listener.submission, submission)
        self.failUnlessEqual(listener.xform, self.xform)

        # test that it works via update as well
        new_vals = { 'age': 20, 'name': 'greg snider' }
        self.xform.update_submission_from_dict(submission, new_vals)

        self.failUnlessEqual(listener.submission.values.get(field__command='age').value, '20')
        self.failUnlessEqual(listener.submission.values.get(field__command='name').value, 'greg snider')

    def testUpdateFromDict(self):
        submission = self.xform.process_sms_submission("survey +age 10 +name matt berg", None)
        self.failUnlessEqual(len(submission.values.all()), 2)

        # now update the form using a dict
        new_vals = { 'age': 20, 'name': 'greg snider' }
        self.xform.update_submission_from_dict(submission, new_vals)

        self.failUnlessEqual(len(submission.values.all()), 2)
        self.failUnlessEqual(submission.values.get(field__command='age').value, '20')
        self.failUnlessEqual(submission.values.get(field__command='name').value, 'greg snider')

        # make sure removal case works
        new_vals = { 'age': 30 }
        self.xform.update_submission_from_dict(submission, new_vals)

        self.failUnlessEqual(len(submission.values.all()), 1)
        self.failUnlessEqual(submission.values.get(field__command='age').value, '30')


