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
        print options
        name = options['n']
        poll_type = options['t']
        question = options['q']
        if options['r'] in ['', '', 'None']:
            default_response = None
        else:

            default_response = options['r']
        print default_response
        contacts = Contact.objects.filter(Q(pk__in=eval(options['c'][1:-1]))
                | Q(groups__pk__in=eval(options['g'][1:-1]))).distinct()
        print contacts
        user = User.objects.get(pk=int(options['u']))
        start_immediately = eval(options['s'])
        response_type = options['e']

        poll = Poll.create_with_bulk(
            name,
            poll_type,
            question,
            default_response,
            contacts,
            user,
            )
        print poll

        poll.response_type = response_type
        poll.save()

        if type == NewPollForm.TYPE_YES_NO:
            poll.add_yesno_categories()

        if settings.SITE_ID:
            poll.sites.add(Site.objects.get_current())
        if start_immediately:
            poll.start()


