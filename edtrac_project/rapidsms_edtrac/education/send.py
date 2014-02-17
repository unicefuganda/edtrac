from rapidsms_httprouter.models import Message
from rapidsms.models import Connection
from unregister.models import Blacklist

def broadcast(text):
    """
    Schedule a one-off message for every non-blacklisted connection.
    """
    connections = [c for c in Connection.objects.all() if not Blacklist.objects.filter(connection=c).exists()]
    Message.mass_text(text, connections)
