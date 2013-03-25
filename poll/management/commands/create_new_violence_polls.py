#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
import traceback

from poll.models import Poll
from unregister.models import Blacklist
from django.conf import settings

from optparse import make_option
from poll.forms import NewPollForm
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from rapidsms.models import Contact
from django.db.models import Q


class Command(BaseCommand):
    help = "Create new violence polls"

    option_list = BaseCommand.option_list + (
        make_option('-n', '--name', dest='n'),
        make_option('-t', '--poll_type', dest='t'),
        make_option('-q', '--question', dest='q'),
        make_option('-r', '--default_response', dest='r'),
        make_option('-c', '--contacts', dest='c'),
        make_option('-u', '--user', dest='u'),
        make_option('-s', '--start_immediately', dest='s'),
        make_option('-e', '--response_type', dest='e'),
        make_option('-g', '--groups', dest='g'),
        )

    def handle(self, **options):
        edtrac_violence_girls = Poll.objects.create(
                name="edtrac_violence_girls",
                type="n",
                question="How many cases of violence against girls were recorded this month? Answer in figures e.g. 5",
                default_response='',
                user=User.objects.get(username='admin'),
                )
        edtrac_violence_girls.sites.add(Site.objects.get_current())
        
        edtrac_violence_boys = Poll.objects.create(
                name="edtrac_violence_boys",
                type="n",
                question="How many cases of violence against boys were recorded this month? Answer in figures e.g. 4",
                default_response='',
                user = User.objects.get(username='admin'),
                )
        edtrac_violence_boys.sites.add(Site.objects.get_current())
        
        edtrac_violence_reported = Poll.objects.create(
                name='edtrac_violence_reported',
                type='n',
                question='How many cases of violence were referred to the Police this month? Answer in figures e.g. 6',
                default_response='',
                user=User.objects.get(username='admin'),
                )
        edtrac_violence_reported.sites.add(Site.objects.get_current())
