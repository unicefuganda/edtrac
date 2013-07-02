# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from django.contrib.auth.models import User
import time
from eav.models import Attribute
from education.models import Role
from poll.models import Poll, Category, Response, ResponseCategory, Rule
from rapidsms.models import Backend, Connection
from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import get_router
from script.models import Script, ScriptStep
from script.utils.outgoing import check_progress


class TestRegistrationProcess(TestCase):
    def setUp(self):
        user ,created = User.objects.get_or_create(username='admin')
        self.auto_reg_script = Script.objects.create(name='Edutrac Registration Script', slug='edtrac_autoreg')
        self.role_poll = Poll.objects.create(name='edtrac_role',
                                             question='Thank you for participating in EduTrac. What is your role? Answer with 1, 2, 3, 4, 5 or 6 for 1=Teacher, 2=Head Teacher, 3=SMC, 4=GEM, 5=DEO, 6=MEO',
                                             type=Poll.TYPE_TEXT,
                                             user=user)
        self.role_step = ScriptStep.objects.create(script=self.auto_reg_script, poll=self.role_poll, order=0,
                                  rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=3)

        self.gender_poll = Poll.objects.create(name='edtrac_gender',
                                             question='Are you female or male?',
                                             type=Poll.TYPE_TEXT,
                                             user=user)
        self.gender_step = ScriptStep.objects.create(script=self.auto_reg_script, poll=self.gender_poll, order=1,
                                  rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=3)

        self.class_poll = Poll.objects.create(name='edtrac_class',
                                             question='Which class do you teach? P3 or P6',
                                             type=Poll.TYPE_TEXT,
                                             user=user)
        self.class_step = ScriptStep.objects.create(script=self.auto_reg_script, poll=self.class_poll, order=2,
                                  rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=3)

        self.district_poll = Poll.objects.create(name='edtrac_district',
                                             question='In which district is your school found?',
                                             type=Poll.TYPE_TEXT,
                                             user=user)
        self.district_step = ScriptStep.objects.create(script=self.auto_reg_script, poll=self.district_poll, order=3,
                                  rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200)

        self.subcounty_poll = Poll.objects.create(name='edtrac_subcounty',
                                             question='What is the name of the sub county in which your school is found?',
                                             type=Poll.TYPE_TEXT,
                                             user=user)
        self.subcounty_step = ScriptStep.objects.create(script=self.auto_reg_script, poll=self.subcounty_poll, order=4,
                                  rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200)

        self.school_poll = Poll.objects.create(name='edtrac_school',
                                             question='What is the name of your school?',
                                             type=Poll.TYPE_TEXT,
                                             user=user)
        self.school_step = ScriptStep.objects.create(script=self.auto_reg_script, poll=self.school_poll, order=5,
                                  rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200)

        self.name_poll = Poll.objects.create(name='edtrac_name',
                                             question='What is your name?',
                                             type=Poll.TYPE_TEXT,
                                             user=user)
        self.name_step = ScriptStep.objects.create(script=self.auto_reg_script, poll=self.name_poll, order=6,
                                  rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200)
        self.welcome_step = ScriptStep.objects.create(
            script=self.auto_reg_script,
            message="Welcome to EduTrac.The information you shall provide contributes to keeping children in school.",
            order=7,rule=ScriptStep.WAIT_MOVEON,start_offset=0,giveup_offset=0,)

        self.backend = Backend.objects.create(name='test')
        self.connection = Connection.objects.create(identity='8675309', backend=self.backend)
        self.create_roles()

    def test_registration_process_for_teacher(self):
        self.create_attribute()
        self.create_role_categories()
        Script.objects.filter(slug='edtrac_autoreg').update(enabled=True)
        self.fake_incoming('join')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.role_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('1')
        #self.create_response_category('1',self.teacher_category)
        check_progress(self.auto_reg_script)
        self.assertEqual(self.class_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('P3')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.district_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('Kamapala')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.subcounty_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('Kampala')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.school_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('St. Marys')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.name_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('test mctester')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.welcome_step.message,Message.objects.filter(direction='O').order_by('-date')[0].text)

    def test_registration_process_for_head_teacher(self):
        self.create_attribute()
        self.create_role_categories()
        Script.objects.filter(slug='edtrac_autoreg').update(enabled=True)
        self.fake_incoming('join')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.role_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('2')
        #self.create_response_category('2',self.head_teacher_category)
        check_progress(self.auto_reg_script)
        self.assertEqual(self.gender_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('Male')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.district_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('Kamapala')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.subcounty_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('Kampala')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.school_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('St. Marys')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.name_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('test mctester')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.welcome_step.message,Message.objects.filter(direction='O').order_by('-date')[0].text)

    def test_registration_process_for_gem(self):
        self.create_attribute()
        self.create_role_categories()
        Script.objects.filter(slug='edtrac_autoreg').update(enabled=True)
        self.fake_incoming('join')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.role_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('4')
        #self.create_response_category('4',self.gem_category)
        check_progress(self.auto_reg_script)
        self.assertEqual(self.district_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('Kamapala')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.subcounty_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('Kampala')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.name_poll.question,Message.objects.filter(direction='O').order_by('-date')[0].text)
        self.fake_incoming('test mctester')
        check_progress(self.auto_reg_script)
        self.assertEqual(self.welcome_step.message,Message.objects.filter(direction='O').order_by('-date')[0].text)

    def fake_incoming(self, message, connection=None):
        if connection is None:
            connection = self.connection
        router = get_router()
        handled = router.handle_incoming(connection.backend.name, connection.identity, message)
        return handled

    def create_attribute(self):
        params = {
            "description": "A response value for a Poll with expected text responses",
            "datatype": Attribute.TYPE_TEXT,
            "enum_group": None,
            "required": False,
            "type": None,
            "slug": "poll_text_value",
            "name": "Text"
        }
        Attribute.objects.create(**params)


    def tearDown(self):
        Poll.objects.all().delete()
        Attribute.objects.all().delete()
        Category.objects.all().delete()
        ResponseCategory.objects.all().delete()
        Role.objects.all().delete()
        Script.objects.all().delete()
        ScriptStep.objects.all().delete()
        Backend.objects.all().delete()
        Connection.objects.all().delete()
        Message.objects.all().delete()
        User.objects.all().delete()
        Rule.objects.all().delete()

    def create_role_categories(self):
        self.teacher_category = Category.objects.create(name='teacher',poll=self.role_poll)
        self.head_teacher_category = Category.objects.create(name='hteacher',poll=self.role_poll)
        self.smc_category = Category.objects.create(name='smc',poll=self.role_poll)
        self.gem_category = Category.objects.create(name='gem',poll=self.role_poll)
        self.deo_category = Category.objects.create(name='deo',poll=self.role_poll)
        self.meo_category = Category.objects.create(name='meo',poll=self.role_poll)
        self.add_rule()

    def create_roles(self):
        Role.objects.create(name='Teachers')
        Role.objects.create(name='Head Teachers')
        Role.objects.create(name='GEM')
        Role.objects.create(name='DEO')
        Role.objects.create(name='MEO')
        Role.objects.create(name='SMC')
        Role.objects.create(name='Other Reporters')

    def create_response_category(self, message,category):
        resp = Response.objects.get(message__text=message,poll=self.role_poll)
        ResponseCategory.objects.create(response=resp,category=category)

    def add_rule(self):
        for category in Category.objects.all():
            r = Rule.objects.create(category=category, rule_type=Rule.TYPE_REGEX,rule_string='^\\s*(3|three)(\\s|[^0-9a-zA-Z])|$')
            r.update_regex()
            r.save()

