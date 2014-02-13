from rapidsms_httprouter.models import Message
from rapidsms.models import Connection
from unregister.models import Blacklist

def broadcast(text):
    """
    Schedule a one-off message for every non-blacklisted connection.
    """
    for connection in Connection.objects.all(): 
        if not Blacklist.objects.filter(connection = connection).exists():
            Message.objects.create(connection = connection, text = text, direction='O', status='Q')
