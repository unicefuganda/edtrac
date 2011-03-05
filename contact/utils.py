from generic.sorters import Sorter
from rapidsms.models import Connection

class DefaultConnectionSorter(Sorter):
    def sort(self, column, object_list, ascending=True):
        order_by = "%s%s" % ('' if ascending else '-', 'identity')
        connections = list(Connection.objects.filter(contact__in=object_list).order_by(order_by).select_related('contact__healthproviderbase__location','contact__healthproviderbase__facility'))
        print connections[0:10]
        full_contact_list = list(object_list)
        toret = []
        for conn in connections:
            if not (conn.contact in toret):
                toret.append(conn.contact)
        noconnections = []
        for c in full_contact_list:
            if not (c in toret):
                noconnections.append(c)
        if ascending:
            toret = toret + noconnections
        else:
            toret = noconnections + toret
        return toret

