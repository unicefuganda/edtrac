import sys
import os
import gzip
import zipfile
from optparse import make_option

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connections, router, transaction, DEFAULT_DB_ALIAS
from django.db.models import get_apps
from django.utils.itercompat import product

from rapidsms_xforms.models import XForm
from rapidsms.models import Connection, Backend
from django.contrib.sites.models import Site

from datetime import datetime

import traceback
import sys, re
import csv

class CommentedFile:
    def __init__(self, f, commentstring="#"):
        self.f = f
        self.commentstring = commentstring

    def next(self):
        line = self.f.next()
        while line.startswith(self.commentstring):
            line = self.f.next()
        return line

    def __iter__(self):
        return self

class Command(BaseCommand):
    help = 'Loads messages from the passed in tab seperated value file.'
    args = "messages.tsv"

    def handle(self, *files, **options):
        connection = connections[DEFAULT_DB_ALIAS]
        self.style = no_style()

        verbosity = int(options.get('verbosity', 1))
        show_traceback = options.get('traceback', False)

        # Keep a count of the messages added
        message_count = 0
        error_count = 0

        cursor = connection.cursor()

        # Start transaction management. All fixtures are installed in a
        # single transaction to ensure that all references are resolved.
        transaction.commit_unless_managed()
        transaction.enter_transaction_management()
        transaction.managed(True)

        for message_file in files:
            try:
                tsv_file = csv.reader(CommentedFile(open(message_file, "rb")))
                for row in tsv_file:
                    message_count += 1

                    if len(row) == 0:
                        continue

                    site = row[0].strip()
                    try:
                        site = Site.objects.get(domain=site)
                        from django.conf import settings
                        settings.SITE_ID = site.pk
                    except Exception as e:
                        print "No site matching: %s" % site
                        error_count += 1
                        continue

                    # build our connection
                    backend = row[1].strip()
                    backend, created = Backend.objects.get_or_create(name=backend)
        
                    # create our connection
                    contact = row[2].strip()
                    connection, created = Connection.objects.get_or_create(backend=backend, identity=contact)

                    # our message
                    message = row[4].strip()

                    # pull out the first word (keyword)
                    keyword = message.split()[0].lower()

                    print ">> %s" % message.strip()

                    # see if this message matches any of our forms
                    forms = XForm.objects.all().filter(active=True, keyword=keyword)
                    if not forms:
                        print "!! No matching xform for: %s" % message
                        error_count += 1
                    else:
                        submission = forms[0].process_sms_submission(message.strip(), connection)


                        # back date if appropriate
                        date = row[3].strip()
                        if date and date.lower() != 'now':
                            try:
                                sub_date = datetime.strptime(date, '%Y-%m-%d')
                                submission.created = sub_date
                                submission.save()
                                print "-- Date set to %s" % date
                            except ValueError as e:
                                print "!! Unable to parse date: %s, should be in format YYYY-MM-DD, leaving date unchanged." % date
                                traceback.print_exc(e)

                        print "<< %s" % submission.response

            except Exception as e:
                traceback.print_exc(e)

        transaction.commit()

        print
        print "%d messages processed.  (%d errors)" % ((message_count - error_count), error_count)
