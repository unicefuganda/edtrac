from rapidsms_httprouter.models import Message
from rapidsms.models import Connection

def broadcast(text):
    for connection in Connection.objects.all(): 
        Message.objects.create(connection_id = connection.id, text = text, direction='O')
