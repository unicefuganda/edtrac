import datetime

from django.core.management.base import BaseCommand

from rapidsms.models import Contact, Connection, Backend

from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import get_router

from django.db import transaction

from rapidsms.messages.outgoing import OutgoingMessage

from script.utils.outgoing import check_progress

class Command(BaseCommand):
    
    @transaction.commit_manually
    def handle(self, **options):
        router = get_router()
        for connection in ScriptProgress.objects.values_list('connection', flat=True).distinct():
            response = check_progress(connection)
            if response:
                router.add_outgoing(connection, response)
            transaction.commit()

