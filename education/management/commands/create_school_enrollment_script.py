'''
Created on May 28, 2013

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
    help = "Create school enrollment termly polls"
    
    def handle(self, **options):
        poll0 = Poll.objects.get(name="total_enrollment_girls")
        poll1 = Poll.objects.get(name="total_enrollment_boys")
        
        script_school_enrollment_termly = Script.objects.create(
                slug="edtrac_school_enrollment_termly",
                name="School Enrollment Termly Script",
                )
        script_school_enrollment_termly.sites.add(Site.objects.get_current())
        
        script_school_enrollment_termly.steps.add(ScriptStep.objects.create(
                script=script_headteacher_violence_monthly,
                poll=poll0,
                order=0,
                rule = ScriptStep.WAIT_MOVEON,
                start_offset=0,
                giveup_offset=14400, # we'll give them four hours to respond
                ))
        script_school_enrollment_termly.steps.add(ScriptStep.objects.create(
                script=script_headteacher_violence_monthly,
                poll=poll1,
                order=1,
                rule=ScriptStep.WAIT_MOVEON, # for polls, this likely means a poll whose answer we aren't particularly concerned with
                start_offset=0, #start immediately after the giveup time has elapsed from the previous step
                giveup_offset=14400, # we'll give them four hours to respond
                ))
