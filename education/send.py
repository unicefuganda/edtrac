from rapidsms_httprouter.models import Message
from rapidsms.models import Connection
from unregister.models import Blacklist

def broadcast(text):
    for connection in Connection.objects.all(): 
        if not Blacklist.objects.filter(connection = connection).exists():
            Message.objects.create(connection_id = connection.id, text = text, direction='O')
