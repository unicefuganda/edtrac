import datetime

from django.core.management.base import BaseCommand
import traceback
from rapidsms.models import Contact, Connection, Backend

from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import get_router

from django.db import transaction

from rapidsms.messages.outgoing import OutgoingMessage

from script.utils.outgoing import check_progress
from script.models import ScriptProgress

class Command(BaseCommand):

    @transaction.commit_manually
    def handle(self, **options):
        try:
            router = get_router()
            for connection in ScriptProgress.objects.values_list('connection', flat=True).distinct():
                connection=Connection.objects.get(pk=connection)
                response = check_progress(connection)
                print response
                if response:
                    router.add_outgoing(connection, response)
                transaction.commit()
        except Exception, exc:
            transaction.rollback()
            print traceback.format_exc(exc)


