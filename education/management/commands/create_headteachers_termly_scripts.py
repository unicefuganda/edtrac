import datetime
import logging
import itertools
from logging import  handlers
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template import Context, Template

import traceback
from rapidsms.models import Contact, Connection, Backend

from rapidsms_httprouter.models import Message

from django.db import transaction

from rapidsms.messages.outgoing import OutgoingMessage

from script.utils.outgoing import check_progress
from script.models import ScriptProgress, Email, Script, ScriptStep
from poll.models import Poll
from optparse import OptionParser, make_option

class Command(BaseCommand):
    help = "Create headteachers termly scripts for teacher deployment, p3 enrollment, p6 enrollment and UPE grant receipt"
    
    def handle(self, **options):
        poll0 = Poll.objects.get(name="edtrac_f_teachers_deployment")
        poll1 = Poll.objects.get(name="edtrac_m_teachers_deployment")
        poll2 = Poll.objects.get(name="edtrac_boysp3_enrollment")
        poll3 = Poll.objects.get(name="edtrac_girlsp3_enrollment")
        poll4 = Poll.objects.get(name="edtrac_boysp6_enrollment")
        poll5 = Poll.objects.get(name="edtrac_girlsp6_enrollment")
        poll6 = Poll.objects.get(name="edtrac_upe_grant")
        
        script_teacher_deployment = Script.objects.create(
                slug="edtrac_teacher_deployment_headteacher_termly",
                name="Teacher Deployment Headteacher Termly Script",
                )
        script_teacher_deployment.sites.add(Site.objects.get_current())
        
        script_p3_enrollment = Script.objects.create(
                slug="edtrac_p3_enrollment_headteacher_termly",
                name="P3 Enrollment Headteacher Termly Script",
                )
        script_p3_enrollment.sites.add(Site.objects.get_current())
        
        script_p6_enrollment = Script.objects.create(
                slug="edtrac_p6_enrollment_headteacher_termly",
                name="P6 Enrollment Headteacher Termly Script",
                )
        script_p6_enrollment.sites.add(Site.objects.get_current())
        
        script_upe_grant = Script.objects.create(
                slug="edtrac_upe_grant_headteacher_termly",
                name="UPE Grant Headteacher Termly Script",
                )
        script_upe_grant.sites.add(Site.objects.get_current())
       
        
        script_teacher_deployment.steps.add(ScriptStep.objects.create(
                script=script_teacher_deployment,
                poll=poll0,
                order=0,
                rule = ScriptStep.WAIT_MOVEON,
                start_offset=0,
                giveup_offset=7200, # we'll give them two hours to respond
                ))
        script_teacher_deployment.steps.add(ScriptStep.objects.create(
                script=script_teacher_deployment,
                poll=poll1,
                order=1,
                rule=ScriptStep.WAIT_GIVEUP, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=7200, # we'll give them two hours to respond
                ))
        script_p3_enrollment.steps.add(ScriptStep.objects.create(
                script=script_p3_enrollment,
                poll=poll2,
                order=0,
                rule=ScriptStep.WAIT_MOVEON, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=7200, # we'll give them two hours to respond
                ))
        script_p3_enrollment.steps.add(ScriptStep.objects.create(
                script=script_p3_enrollment,
                poll=poll3,
                order=1,
                rule = ScriptStep.WAIT_GIVEUP,
                start_offset=0,
                giveup_offset=7200, # we'll give them two hours to respond
                ))
        script_p6_enrollment.steps.add(ScriptStep.objects.create(
                script=script_p6_enrollment,
                poll=poll4,
                order=0,
                rule=ScriptStep.WAIT_MOVEON, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=7200, # we'll give them two hours to respond
                ))
        script_p6_enrollment.steps.add(ScriptStep.objects.create(
                script=script_p6_enrollment,
                poll=poll5,
                order=1,
                rule=ScriptStep.WAIT_GIVEUP, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=7200, # we'll give them two hours to respond
                ))
        script_upe_grant.steps.add(ScriptStep.objects.create(
                script=script_upe_grant,
                poll=poll6,
                order=0,
                rule=ScriptStep.WAIT_GIVEUP, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=10800, # we'll give them two hours to respond
                ))