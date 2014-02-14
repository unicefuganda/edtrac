from generic.forms import ActionForm
from rapidsms.models import Connection
from unregister.models import Blacklist

class BlacklistForm(ActionForm):
    """ abstract class for all the filter forms"""
    action_label = 'Blacklist/Opt-out Users'
    def perform(self, request, results):
        if request.user and request.user.has_perm('unregister.add_blacklist'):
            connections = Connection.objects.filter(contact__in=results)
            for c in connections:
                Blacklist.objects.get_or_create(connection=c)
            return ('You blacklisted %d numbers' % len(connections), 'success',)
        else:
            return ("You don't have permissions to blacklist numbers", 'error',)
