from rapidsms_httprouter.models import Message
from ureport.models import MassText
from poll.models import Poll

def get_messages():
    return Message.objects.filter(direction='I')

def get_mass_messages():
    return [(p.question, p.start_date, p.user.username, p.contacts.count(), 'Poll Message') for p in Poll.objects.exclude(start_date=None)] + [(m.text, m.date, m.user.username, m.contacts.count(), 'Mass Text') for m in MassText.objects.all()]

