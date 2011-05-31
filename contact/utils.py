from rapidsms_httprouter.models import Message
from ureport.models import MassText
from poll.models import Poll

def get_messages(**kwargs):
    request = kwargs.pop('request')
    if request.user.is_authenticated():
        return Message.objects.filter(direction='I', connection__contact__groups__in=request.user.groups.all())

    return Message.objects.filter(direction='I')

def get_mass_messages(**kwargs):
    return [(p.question, p.start_date, p.user.username, p.contacts.count(), 'Poll Message') for p in Poll.objects.exclude(start_date=None)] + [(m.text, m.date, m.user.username, m.contacts.count(), 'Mass Text') for m in MassText.objects.all()]

