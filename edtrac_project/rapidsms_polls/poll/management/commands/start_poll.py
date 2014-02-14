#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand


from poll.models import Poll

from optparse import make_option


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-p', '--poll', dest='p'),
        )

    def handle(self, **options):
        poll_pk = int(options['p'])
        try:
            poll=Poll.objects.get(pk=poll_pk)
            poll.start()
        except Poll.DoesNotExist:
            pass





