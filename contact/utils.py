from rapidsms_httprouter.models import Message

def get_messages():
    return Message.objects.filter(direction='I')
