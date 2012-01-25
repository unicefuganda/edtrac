from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.auth.models import User, Group
from script.models import *

def init_structures():
    if 'django.contrib.sites' in settings.INSTALLED_APPS:
        site_id = getattr(settings, 'SITE_ID', 5)
        Site.objects.get_or_create(pk=site_id, defaults={'domain':'rapidedtrac.com'})
    init_groups()
    init_autoreg()
    init_scripts()

def init_groups():
    for g in ['Teachers', 'Head Teachers', 'SMC', 'GEM', 'CCT', 'DEO', 'District Officials', 'Ministry Officials', 'UNICEF Officials', 'Other Reporters']:
        Group.objects.get_or_create(name=g)

def init_autoreg():
    script, created = Script.objects.get_or_create(
            slug="edtrac_autoreg", defaults={
            'name':"Education monitoring auto registration script",
            'enabled':False})
    if created:
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            script.sites.add(Site.objects.get_current())
        user, created = User.objects.get_or_create(username="admin")
        
        role_poll = Poll.objects.create(name='edtrac_role', user=user, type=Poll.TYPE_TEXT, question='Thank you for participating in EdTrac. What is your role? Choose ONE: Teacher, Head Teacher, SMC, GEM', default_response='')
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=role_poll,
            order=0,
            rule=ScriptStep.RESEND_MOVEON,
            num_tries=1,
            start_offset=0,
            retry_offset=86400,
            giveup_offset=86400,
        ))
        gender_poll = Poll.objects.create(name='edtrac_gender', user=user, type=Poll.TYPE_TEXT, question='Are you female or male?', default_response='')
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=gender_poll,
            order=1,
            rule=ScriptStep.RESEND_MOVEON,
            num_tries=1,
            start_offset=0,
            retry_offset=86400,
            giveup_offset=86400,
        ))
        class_poll = Poll.objects.create(name='edtrac_class', user=user, type=Poll.TYPE_TEXT, question='Which class do you teach? P3 or P6', default_response='')
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=class_poll,
            order=2,
            rule=ScriptStep.RESEND_MOVEON,
            num_tries=1,
            start_offset=0,
            retry_offset=86400,
            giveup_offset=86400,
        ))
        district_poll = Poll.objects.create(name='edtrac_district', user=user, type=Poll.TYPE_LOCATION, question='What is the name of your district?', default_response='')
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=district_poll,
            order=3,
            rule=ScriptStep.STRICT_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))
        subcounty_poll = Poll.objects.create(name='edtrac_subcounty',user=user,type=Poll.TYPE_TEXT, question='What is the name of your sub county?', default_response='')
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=subcounty_poll,
            order=4,
            rule=ScriptStep.RESEND_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))
        school_poll = Poll.objects.create(name='edtrac_school', user=user, type=Poll.TYPE_TEXT, question='What is the name of your school?', default_response='')
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=school_poll,
            order=5,
            rule=ScriptStep.RESEND_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))
        name_poll = Poll.objects.create(name='edtrac_name', user=user, type=Poll.TYPE_TEXT, question='What is your name?', default_response='')
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=name_poll,
            order=6,
            rule=ScriptStep.RESEND_MOVEON,
            num_tries=1,
            start_offset=60,
            retry_offset=86400,
            giveup_offset=86400,
        ))
        script.steps.add(ScriptStep.objects.create(
            script=script,
            message="Welcome EdTrac.The information you shall provide contributes to keeping children in school.",
            order=7,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=60,
            giveup_offset=0,
        ))
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            polls = Poll.objects.filter(name__in=['edtrac_role', 'edtrac_gender', 'edtrac_class', 'edtrac_district', 'edtrac_subcounty', 'edtrac_school', 'edtrac_name'])
            for poll in polls:
                poll.sites.add(Site.objects.get_current())
                
def init_scripts():
    simple_scripts = {
	    'teachers weekly':[(Poll.TYPE_NUMERIC, 'edtrac_boysp3_attendance', 'How many P3 boys are at school today?',),
                           (Poll.TYPE_NUMERIC, 'edtrac_boysp6_attendance', 'How many P6 boys are at school today?',),
                           (Poll.TYPE_NUMERIC, 'edtrac_girlsp3_attendance', 'How many P3 girls are at school today?',),
                           (Poll.TYPE_NUMERIC, 'edtrac_girlsp6_attendance', 'How many P6 girls are at school today?',),
                           (Poll.TYPE_NUMERIC, 'edtrac_p3curriculum_progress', 'What sub theme number you were teaching this week? (P3) ',),
                           (Poll.TYPE_TEXT, 'edtrac_p3curriculum_progress', 'What sub theme number of the P3 Literacy curriculum are you teaching this week? ',),
                           ],
        'head teachers weekly':[(Poll.TYPE_NUMERIC, 'edtrac_f_teachers_attendance', 'How many female teachers are at school today?',),
                                (Poll.TYPE_NUMERIC, 'edtrac_m_teachers_attendance', 'How many male teachers are at school today?',),
                           ],
        'smc weekly':[(Poll.TYPE_TEXT, 'edtrac_head_teachers_attendance', 'Has the head teacher been at school for at least 3 days? Answer YES or NO', True),
                           ],
        #'teachers monthly':[(Poll.TYPE_TEXT, 'edtrac_p3curriculum_progress', 'What sub theme number of the P3 Literacy curriculum are you teaching this week? ',),                 ],
        'head teachers monthly':[(Poll.TYPE_NUMERIC, 'edtrac_headteachers_abuse', 'How many abuse cases were recorded in the record book this month?',),
                                (Poll.TYPE_TEXT, 'edtrac_headteachers_meals', 'How many children do you think had lunch today? Reply with ONE of the following; 0%, 25%, 50%, 75% or 100%',),
                           ],
        'smc monthly':[(Poll.TYPE_TEXT, 'edtrac_smc_meals', 'How many children do you think had lunch today? Reply with ONE of the following; 0%, 25%, 50%, 75% or 100%',),
                           ],
        'gem monthly':[(Poll.TYPE_TEXT, 'edtrac_gem_headteacher_present', 'Name the schools where the Head teacher was present at your last visit? Separate schools with a comma e.g St Peters PS, St John PS',),
                       (Poll.TYPE_TEXT, 'edtrac_gem_headteacher_absent', 'Name the schools where the Head teacher was absent at your last visit? Separate schools with a comma e.g St Peters PS, St John PS',),
                           ],
        'head teachers termly':[(Poll.TYPE_NUMERIC, 'edtrac_boysp3_enrollment', 'How many boys are enrolled in P3 this term?',),
                                (Poll.TYPE_NUMERIC, 'edtrac_boysp6_enrollment', 'How many boys are enrolled in P6 this term?',),
                                (Poll.TYPE_NUMERIC, 'edtrac_girlsp3_enrollment', 'How many girls are enrolled in P3 this term?',),
                                (Poll.TYPE_NUMERIC, 'edtrac_girlsp6_enrollment', 'How many girls are enrolled in P6 this term?',),
                                (Poll.TYPE_NUMERIC, 'edtrac_f_teachers_deployment', 'How many female teachers are deployed in your school this term?',),
                                (Poll.TYPE_NUMERIC, 'edtrac_m_teachers_deployment', 'How many male teachers are deployed in your school this term?',),
                                (Poll.TYPE_TEXT, 'edtrac_upe_grant', 'Has the UPE grant been displayed on the school notice board? Answer YES or NO',True),
                           ],
        'smc termly':[(Poll.TYPE_TEXT, 'edtrac_smc_upe_grant', 'Has UPE capitation grant been displayed on the school notice board? Answer YES or NO',True),
                      (Poll.TYPE_NUMERIC, 'edtrac_smc_meetings', 'How many SMC meetings have you held this term? Give number of meetings held, if none, reploy 0.',),
                           ],
   }

    user, created = User.objects.get_or_create(username='admin')
    for script_name, polls in simple_scripts.items():
        script, created = Script.objects.get_or_create(
            slug="edtrac_%s" % script_name.lower().replace(' ', '_'), defaults={
            'name':"Education monitoring %s script" % script_name,
            'enabled':False})
        if created:
            script.sites.add(Site.objects.get_current())
            step = 0
            for poll_info in polls:
                poll = Poll.objects.create(
                    user=user, \
                    type=poll_info[0], \
                    name=poll_info[1],
                    question=poll_info[2], \
                    default_response='', \
                )
                poll.sites.add(Site.objects.get_current())

                if len(poll_info) > 3 and poll_info[3]:
                    poll.add_yesno_categories()
                script.steps.add(ScriptStep.objects.create(
                    script=script,
                    poll=poll,
                    order=step,
                    rule=ScriptStep.RESEND_MOVEON,
                    num_tries=1,
                    start_offset=60,
                    retry_offset=86400,
                    giveup_offset=86400,
                ))
                step = step + 1
