import datetime
from django.db import models, transaction
#import django
import django.dispatch
from django.db import connection as db_connection
from rapidsms.models import Contact, Connection

from .managers import ForUpdateManager
from django.conf import settings

mass_text_sent = django.dispatch.Signal(providing_args=["messages", "status"])

DIRECTION_CHOICES = (
    ("I", "Incoming"),
    ("O", "Outgoing"))

STATUS_CHOICES = (
    ("R", "Received"),
    ("H", "Handled"),

    ("P", "Processing"),
    ("L", "Locked"),

    ("Q", "Queued"),
    ("S", "Sent"),
    ("D", "Delivered"),

    ("C", "Cancelled"),
    ("E", "Errored")
)

#
# Allows us to use SQL to lock a row when setting it to 'locked'.  Without this
# in a multi-process environment like Gunicorn we'll double send messages.
#
# See: https://coderanger.net/2011/01/select-for-update/
#
class MessageBatch(models.Model):
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)

class Message(models.Model):
    connection = models.ForeignKey(Connection, related_name='messages')
    text = models.TextField(db_index=True)
    direction = models.CharField(max_length=1, choices=DIRECTION_CHOICES, db_index=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, db_index=True)
    date = models.DateTimeField(auto_now_add=True)
    priority = models.IntegerField(default=10, db_index=True)

    in_response_to = models.ForeignKey('self', related_name='responses', null=True)
    application = models.CharField(max_length=100, null=True)

    batch = models.ForeignKey(MessageBatch, related_name='messages', null=True)
    # set our manager to our update manager
    objects = ForUpdateManager()

    def __unicode__(self):
        # crop the text (to avoid exploding the admin)
        if len(self.text) < 60: str = self.text
        else: str = "%s..." % (self.text[0:57])

        to_from = (self.direction == "I") and "to" or "from"
        return "%s (%s %s)" % (str, to_from, self.connection.identity)

    def as_json(self):
        return dict(id=self.pk,
                    contact=self.connection.identity, backend=self.connection.backend.name,
                    direction=self.direction, status=self.status, text=self.text,
                    date=self.date.isoformat())

    @classmethod
    @transaction.commit_on_success
    def mass_text(cls, text, connections, status='P'):
        batch = MessageBatch.objects.create(status='Q')
        insert_list = []
        d = datetime.datetime.now()
        c = db_connection.cursor()
        
        for db_name in settings.DATABASES:
            """
            Databases other than PostGreSQL don't have the "RETURNING" keyword for their INSERT query (its a postgresql SQL extension).
            Thus Sqlite, MySQL etal will run two queries, one to insert messages another to retrieve the pks of the inserted rows.
            PostGreSQL only runs one INSERT query and uses "RETURNING" to return pks with the same query.
            """
            if not settings.DATABASES[db_name]['ENGINE'] == 'django.db.backends.postgresql_psycopg2':
                sql = 'insert into rapidsms_httprouter_message (text, date, direction, status, batch_id, connection_id, priority) values '
                
                for connection in connections:
                    insert_list.append("('%s', '%s', 'O', '%s', %d, %d, %d)" % \
                    (text, \
                     d.strftime('%Y-%m-%d %H:%M:%S'), \
                     status, \
                     batch.pk, \
                     connection.pk,\
                     10))
                
                sql = "%s %s" % (sql, ",".join(insert_list))
                
                c.execute(sql)
                sql2 = 'select id from rapidsms_httprouter_message order by date desc limit %s' % len(connections)
                pks = c.execute(sql2).fetchall()
            else:
                sql = 'insert into rapidsms_httprouter_message (text, date, direction, status, batch_id, connection_id) values '
            
                for connection in connections:
                    insert_list.append("('%s', '%s', 'O', '%s', %d, %d)" % \
                    (text, \
                     d.strftime('%Y-%m-%d %H:%M:%S'), \
                     status, \
                     batch.pk, \
                     connection.pk))
                     
                sql = "%s %s returning id" % (sql, ",".join(insert_list))
                
                c.execute(sql)
                pks = c.fetchall()
                
        toret = Message.objects.filter(pk__in=[pk[0] for pk in pks])
        mass_text_sent.send(sender=batch, messages=toret, status=status)
        return toret


