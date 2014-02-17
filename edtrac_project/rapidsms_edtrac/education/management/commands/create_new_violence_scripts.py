'''
Created on Mar 25, 2013

@author: raybesiga
'''

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
    help = "Create monthly headteachers' violence polls"
    
    def handle(self, **options):
        poll0 = Poll.objects.get(name="edtrac_violence_girls")
        poll1 = Poll.objects.get(name="edtrac_violence_boys")
        poll2 = Poll.objects.get(name="edtrac_violence_reported")
        poll3 = Poll.objects.get(name="edtrac_headteachers_meals")
        
        script_headteacher_violence_monthly = Script.objects.create(
                slug="edtrac_headteacher_violence_monthly",
                name="Headteacher Violence Monthly Script",
                )
        script_headteacher_violence_monthly.sites.add(Site.objects.get_current())
        
        script_headteacher_meals_monthly = Script.objects.create(
                slug="edtrac_headteacher_meals_monthly",
                name="Headteacher Meals Monthly Script",
                )
        script_headteacher_meals_monthly.sites.add(Site.objects.get_current())
        
        script_headteacher_violence_monthly.steps.add(ScriptStep.objects.create(
                script=script_headteacher_violence_monthly,
                poll=poll0,
                order=0,
                rule = ScriptStep.WAIT_MOVEON,
                start_offset=0,
                giveup_offset=10800, # we'll give them two hours to respond
                ))
        script_headteacher_violence_monthly.steps.add(ScriptStep.objects.create(
                script=script_headteacher_violence_monthly,
                poll=poll1,
                order=1,
                rule=ScriptStep.WAIT_MOVEON, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=10800, # we'll give them two hours to respond
                ))
        script_headteacher_violence_monthly.steps.add(ScriptStep.objects.create(
                script=script_headteacher_violence_monthly,
                poll=poll2,
                order=2,
                rule=ScriptStep.WAIT_MOVEON, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=10800, # we'll give them two hours to respond
                ))
        script_headteacher_meals_monthly.steps.add(ScriptStep.objects.create(
                script=script_headteacher_meals_monthly,
                poll=poll3,
                order=0,
                rule = ScriptStep.WAIT_MOVEON,
                start_offset=0,
                giveup_offset=10800, # we'll give them two hours to respond
                ))
        