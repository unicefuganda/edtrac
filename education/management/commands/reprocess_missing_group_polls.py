from django.core.exceptions import MultipleObjectsReturned

from django.core.management.base import BaseCommand
from education.models import reschedule_termly_polls
from optparse import OptionParser, make_option
from poll.models import Poll, Response, ResponseCategory
from education.models import EmisReporter
from script.models import ScriptSession, Script
from rapidsms_httprouter.models import Message
from rapidsms.messages.incoming import IncomingMessage
from rapidsms.contrib.locations.models import Location
import re

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (make_option("-p", "--poll_name", dest="poll_name"),
                                             make_option("-g", "--group_name", dest="group_name"),
                                             make_option("-s", "--script_slug", dest="script_slug"))

    def process_response(self, poll, incoming_message_instance, message_instance): # not nice names.
        db_message = None
        if hasattr(incoming_message_instance, 'db_message'):
            db_message = incoming_message_instance.db_message
        else:
            db_message=incoming_message_instance

        resp = Response.objects.create(poll=poll, message=message_instance, contact=db_message.connection.contact, date=db_message.date)

        if (poll.type == Poll.TYPE_LOCATION):
            location_template = STARTSWITH_PATTERN_TEMPLATE % '[a-zA-Z]*'
            regex = re.compile(location_template, re.IGNORECASE)
            if regex.search(incoming_message_instance.text):
                spn = regex.search(incoming_message_instance.text).span()
                location_str = incoming_message_instance.text[spn[0]:spn[1]]
                area = None
                area_names = Location.objects.all().values_list('name', flat=True)
                area_names_lower = [ai.lower() for ai in area_names]
                area_names_matches = difflib.get_close_matches(location_str.lower(), area_names_lower)
                if area_names_matches:
                    area = Location.objects.filter(name__iexact=area_names_matches[0])[0]
                    resp.eav.poll_location_value = area
                    resp.save()
                else:
                    resp.has_errors = True

            else:
                resp.has_errors = True

        elif (poll.type == Poll.TYPE_NUMERIC):
            try:
                regex = re.compile(r"(-?\d+(\.\d+)?)")
                #split the text on number regex. if the msg is of form
                #'19'or '19 years' or '19years' or 'age19'or 'ugx34.56shs' it returns a list of length 4
                msg_parts = regex.split(incoming_message_instance.text)
                if len(msg_parts) == 4 :
                    resp.eav.poll_number_value = float(msg_parts[1])
                else:
                    resp.has_errors = True
            except IndexError:
                resp.has_errors = True

        elif ((poll.type == Poll.TYPE_TEXT) or (poll.type == Poll.TYPE_REGISTRATION)):
            resp.eav.poll_text_value = incoming_message_instance.text
            if poll.categories:
                for category in poll.categories.all():
                    for rule in category.rules.all():
                        regex = re.compile(rule.regex, re.IGNORECASE)
                        if regex.search(incoming_message_instance.text.lower()):
                            rc = ResponseCategory.objects.create(response=resp, category=category)
                            resp.categories.add(rc)
                            if category.error_category:
                                resp.has_errors = True
                            break

        elif poll.type in Poll.TYPE_CHOICES:
            typedef = Poll.TYPE_CHOICES[poll.type]
            try:
                cleaned_value = typedef['parser'](incoming_message_instance.text)
                if typedef['db_type'] == Attribute.TYPE_TEXT:
                    resp.eav.poll_text_value = cleaned_value
                elif typedef['db_type'] == Attribute.TYPE_FLOAT or\
                     typedef['db_type'] == Attribute.TYPE_INT:
                    resp.eav.poll_number_value = cleaned_value
                elif typedef['db_type'] == Attribute.TYPE_OBJECT:
                    resp.eav.poll_location_value = cleaned_value
            except ValidationError as e:
                resp.has_errors = True

        if not resp.categories.all().count() and poll.categories.filter(default=True).count():
            resp.categories.add(ResponseCategory.objects.create(response=resp, category=poll.categories.get(default=True)))
            if poll.categories.get(default=True).error_category:
                resp.has_errors = True

        resp.save()
        outgoing_message = None # disabled any outgoining message
        if not outgoing_message:
            return (resp, None,)


    def handle(self, **options):

        if not options['poll_name']:
            poll_name = raw_input('Name of poll: ')
        if not options['group_name']:
            group_name = raw_input('Name of group: ')
        if not options['script_slug']:
            script_slug = raw_input('Script slug: ')
        try:
            poll = Poll.objects.get(name = poll_name)
            script = Script.objects.get(slug = script_slug)
            conns = EmisReporter.objects.filter(groups__name=group_name).\
                filter(connection__identity__in=ScriptSession.objects.filter(script=script, end_time=None).\
                    values_list('connection__identity',flat=True)).\
                    values_list('connection__identity',flat=True)

            count = Message.objects.filter(direction='I', poll__responses=None,connection__identity__in=conns).count()

            reg_no = '^\\s*(no|nope|nah|nay|n)(\\s|[^a-zA-Z]|$)'
            regex_no = re.compile(reg_no, re.IGNORECASE)
            reg_yes = '^\\s*(yes|yeah|yep|yay|y)(\\s|[^a-zA-Z]|$)'
            regex_yes = re.compile(reg_yes, re.IGNORECASE)


            for m in Message.objects.filter(direction='I', poll__responses=None,connection__identity__in=conns):

                if regex_no.search(m.text.lower()) or regex_yes.search(m.text.lower()): # brutally make sure YES or No is some variant of text
                    _incoming_message = IncomingMessage(m.connection, m.text, received_at=m.date)
                    self.process_response(poll, _incoming_message, m)
                    count -= 1
                    if count%20 == 0:
                        #just for reporting purposes in terminal
                        self.stdout.write('\n%r - %r - %r (%r left) ' % (m.text, m.connection.identity, m.date, count))


            self.stdout.write('\ndone correcting the response!!!')
        except MultipleObjectsReturned, DoesNotExist:
            raise DoesNotExist
