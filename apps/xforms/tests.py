"""
Basic tests for XForms
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.test.client import Client
from .models import XForm, XFormField, XFormFieldConstraint

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
                                      'description': 'desc2' }, follow=True)

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

    def testFieldConstraints(self):
        user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
        user.save()

        xform = XForm(name='test', keyword='test', owner=user)

        xform.save()

        field = XFormField(type='INT', caption='number', command='number', xform=xform)
        field.save()

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








