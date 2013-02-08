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
    help = "Create a teachers weekly script for P3 and P6 teachers"
    
    def handle(self, **options):
        poll0 = Poll.objects.get(name="edtrac_boysp3_attendance")
        poll1 = Poll.objects.get(name="edtrac_girlsp3_attendance")
        poll2 = Poll.objects.get(name="edtrac_p3curriculum_progress")
        poll3 = Poll.objects.get(name="edtrac_boysp6_attendance")
        poll4 = Poll.objects.get(name="edtrac_girlsp6_attendance")
        
        script_p3 = Script.objects.create(
                slug="edtrac_p3_teachers_weekly",
                name="Revised P3 Teachers Weekly Script",
                )
        script_p3.sites.add(Site.objects.get_current())
        
        script_p6 = Script.objects.create(
                slug="edtrac_p6_teachers_weekly",
                name="Revised P6 Teachers Weekly Script",
                )
        script_p6.sites.add(Site.objects.get_current())
       
        
        script_p3.steps.add(ScriptStep.objects.create(
                script=script_p3,
                poll=poll0,
                order=0,
                rule = ScriptStep.WAIT_MOVEON,
                start_offset=0,
                giveup_offset=7200, # we'll give them two hours to respond
                ))
        script_p3.steps.add(ScriptStep.objects.create(
                script=script_p3,
                poll=poll1,
                order=1,
                rule=ScriptStep.WAIT_MOVEON, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=7200, # we'll give them two hours to respond
                ))
        script_p3.steps.add(ScriptStep.objects.create(
                script=script_p3,
                poll=poll2,
                order=2,
                rule=ScriptStep.WAIT_GIVEUP, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=7200, # we'll give them two hours to respond
                ))
        script_p6.steps.add(ScriptStep.objects.create(
                script=script_p6,
                poll=poll3,
                order=0,
                rule = ScriptStep.WAIT_MOVEON,
                start_offset=0,
                giveup_offset=7200, # we'll give them two hours to respond
                ))
        script_p6.steps.add(ScriptStep.objects.create(
                script=script_p6,
                poll=poll4,
                order=1,
                rule=ScriptStep.WAIT_GIVEUP, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=7200, # we'll give them two hours to respond
                ))