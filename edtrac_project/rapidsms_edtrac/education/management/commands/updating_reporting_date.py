from rapidsms.models import Connection

__author__ = 'kenneth'
for a in Connection.objects.all():
    try:
        ls = a.submissions.latest('created')
        r = a.contact.emisreporter
        r.last_reporting_date = ls.created
        r.save()
        print r, 'update last reporting date to', r.last_reporting_date
    except Exception as e:
        print 'not updated', e
