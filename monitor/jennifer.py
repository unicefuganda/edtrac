#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Samuel Sekiwere <sekiskylink@gmail.com>

import web
import urllib
import httplib
import logging
import psycopg2
import re
from datetime import datetime
from datetime import timedelta

class AppURLopener(urllib.FancyURLopener):
	version = "QOS /0.1"

urllib._urlopener = AppURLopener()

render = web.template.render('/var/log/qos')

logging.basicConfig( format='%(asctime)s:%(levelname)s:%(message)s', filename='/tmp/qos.log',
		datefmt='%Y-%m-%d %I:%M:%S', level=logging.DEBUG)

#DB confs
db_host = 'localhost'
db_name = 'jennifer'
db_user = 'postgres'
db_passwd = 'postgres'


urls = (
        "/qos", "HandleReceivedQosMessage",
        "/dlr", "HandleDlr",
        "/send", "SendQosMessages",
        "/check", "CheckModems",
        "/monitor", "MonitorQosMessages",
        "/manage", "DisableEnableBackend",
        "info", "Info",
        "/test", "Test",
        )

#web.config.smtp_server = 'mail.mydomain.com'

app = web.application(urls, globals())
db = web.database(
    dbn='postgres',
    user=db_user,
    pw=db_passwd,
    db=db_name,
        host=db_host
    )

QOS_RECIPIENTS = [
        ('Samuel', 'sekiskylink@gmail.com')
        ]
MODEM_STATUS_RECIPIENTS = [
        ('Samuel', 'sekiskylink@gmail.com')
        ]


RECIEVE_URL = 'http://messenger.unicefuganda.org/router/receive/?password=p73xvyqi&backend=%s&sender=%s&message=%s'

KANNEL_STATUS_URL = 'http://localhost:13000/status'

#SENDSMS_URL = ('http://localhost:13013/cgi-bin/sendsms?username=tester&password=foobar&from=%(from)s&'
#                'to=%(to)s&text=%(text)s&smsc=%(backend)s')
SENDSMS_URL = 'http://localhost:13013/cgi-bin/sendsms?username=tester&password=foobar'
QOS_INTERVAL = {'hours':1, 'minutes':0, 'offset':5}
DEFAULT_EMAIL_SENDER = 'root@uganda.rapidsms.org'

## Helper Classes and Functions
class GetBackends(object):
    def __init__(self,db,btype='s',active='t'):
        self.db = db
        self.backend_type = btype
        self.active = active
    def get(self):
        b_query = ("SELECT id,name,identity, smsc_name FROM backends WHERE btype = '%s' AND active = %s")
        query = b_query %(self.backend_type, self.active)
        backends = self.db.query(query)
        return backends

class GetAllowedModems(object):
    def __init__(self,db,shortcode_id):
        self.db = db
        self.shortcode_id = shortcode_id
    def get(self):
        t_query = ("SELECT id, name, identity, smsc_name, active FROM backends "
                    "WHERE id IN (SELECT unnest(allowedlist) FROM shortcode_allowed_modems WHERE id = %s) AND active = %s")
        query = t_query % (self.shortcode_id, True)
        res = self.db.query(query)
        return res

def IsModemActive(modem_smscname):
    try:
        f = urllib.urlopen(KANNEL_STATUS_URL)
        x = f.readlines()
    except IOError, (instance):
        return False
    p = x[:]
    status = 'offline'
    for l in p:
        if not l.strip():
            continue
        pattern = re.compile(r'%s'%modem_smscname)
        if pattern.match(l.strip()):
            status = l.strip().split()[2].replace('(','')
    return True if status == 'online' else False

def sendsms(frm, to, msg,smsc):
    params = {'from':frm,'to':to,'text':msg,'smsc':smsc}
    surl = SENDSMS_URL
    if surl.find('?'):
        c = '&'
    else: c = '?'
    url = surl + c + urlencode(params)
    try:
        s = urlopen(url)
        ret = s.readlines()
    except IOError, (instance):
        ret = "Error."
    return ret[:]

# Logs Sent Message to out message table
def log_message(dbconn,msg_dict):
    #query = "INSERT INTO messages (%s) VALUES %s"%(','.join([k for k in msg_dict.keys()]),
    #        tuple(['%s'%k for k in msg_dict.keys()]))
    #dbconn.query(query)
    dbconn.insert('messages',backend_id=msg_dict['backend_id'], msg_out=msg_dict['msg_out'],
            status_out=msg_dict['status_out'], destination=msg_dict['destination'])


def send_email(fro, recipient, subject, msg):
    web.sendmail('root@uganda.rapidsms.org',recipient, subject, msg)

def SendModemAvailabilityAlert(modem_smscname):
    #send email
    #msg, recipient = ['Hello %s,\n The '+ modem_smscname + ' is not on-line!'%(name),email for name, email in MODEM_STATUS_RECIPIENTS]
    subject = 'QOS Modem Alert'
    for name, email in MODEM_STATUS_RECIPIENTS:
        msg = 'Hello %s,\nThe %s is not on-line!\n\nRegards,\nJenifer'%(name, modem_smscname)
        send_email(DEFAULT_EMAIL_SENDER, email, subject, msg)

def get_qos_time_offset():
    qos_interval = QOS_INTERVAL
    time_offset = datetime.now() - timedelta(hours=qos_interval['hours'],
                    minutes=(qos_interval['minutes'] + qos_interval['offset']))
    return time_offset


#Page Handlers
class HandleReceivedQosMessage:
    def GET(self):
        params = web.input(
                sender='',
                receiver='',
                backend='',
                message=''
                )
        x = GetBackends(db, 's', True)
        shortcode_backends = x.get()
        shortcodes = [s['identity'] for s in shortcode_backends]
        if params.sender.lower() not in shortcodes:
            return "Ignored, black listed sender!"
        msg = params.message.strip()
        if not re.match(r'^\d{4}-\d{2}-\d{2}\s\d{2}$', msg):
            return "Message not in format we want!"
        # Now log message to DB in msg_in
        modems  = GetBackends(db, 'm' ,True).get()
        modem_numbers = [m['identity'] for m in GetBackends(db, 'm', True).get()]
        if params.receiver not in modem_numbers:
            return "Message Ingnored, receiver not one of our modem numbers!"
        backend_id = [b['id'] for b in modems if b['smsc_name'] == params.backend][0]
        msg_in = msg
        with db.transaction():
            db.update('messages', msg_in=msg_in, ldate=datetime.now(),
                    where=web.db.sqlwhere({'msg_out':msg, 'backend_id':backend_id, 'destination':params.sender}))
            logging.debug("[%s] Received SMS [SMSC: %s] [from: %s] [to: %s] [msg: %s]"%('/qos',
                params.backend, params.sender, params.receiver, msg))
        return "Done!"

class HandleDlr:
    def GET(self):
        params = web.input(
                source='',
                destination='',
                message='',
                dlrvalue=''
                )
        return "It works!"

class SendQosMessages:
    def GET(self):
        x = GetBackends(db,'s',True)
        shortcode_backends = x.get()
        applied_modems = [] # for logging
        failed_modems = []
        logging.debug("[%s] Started Sending QOS Messages"%('/send'))
        for shortcode in shortcode_backends:
            y = GetAllowedModems(db, shortcode['id'])
            allowed_modems = y.get()
            for modem in allowed_modems:
                #Check if modem SMSC is active if not SEND Mail
                if not IsModemActive(modem['smsc_name']):
                    SendModemAvailabilityAlert(modem['smsc_name'])
                    failed_modems.append(modem['smsc_name'])
                    continue
                #now you can send using this modem
                mgs = datetime.now().strftime('%Y-%m-%d %H')
                _from = modem['identity']
                to = shortcode['identity']
                smsc = modem['smsc_name']
                applied_modems.append(smsc)
                res = sendsms(_from, to, msg, smsc)
                status = 'S' if res.find('Accept') else 'Q'
                if res.find('Error'):
                    send_email("SMS Send Error", 'sekiskylink@gmail.com',
                            'Hi,\nError sending from %s to %s.\n\nRegards,\nJenifer'%(modem['name'],shortcode['identity']))
                    status = 'E'

                #create log message dict
                backend_id = modem['id']
                log_message_dict = {
                        'backend_id':backend_id,
                        'msg_out':msg,
                        'destination':shortcode['identity'],
                        'status_out':status
                        }
                with db.transaction():
                    log_message(db, log_message_dict)
        logging.debug("[%s] Sent QOS messages using %s: Failed = %s"%('/send', applied_modems, set(failed_modems)))
        return "Done!"

class MonitorQosMessages:
    def GET(self):
        x = GetBackends(db,'s',True)
        shortcode_backends = x.get()
        time_offset = get_qos_time_offset()
        logging.debug("[%s] Started Mornitoring"%('/monitor'))
        for shortcode in shortcode_backends:
            y = GetAllowedModems(db, shortcode['id'])
            allowed_modems = y.get()
            for modem in allowed_modems:
                t_query = ("SELECT id FROM messages WHERE cdate > '%s' AND msg_out = msg_in AND msg_out <> '' "
                            " AND backend_id = %s AND destination = '%s'")
                query = t_query % (time_offset, modem['id'], shortcode['identity'])
                res = db.query(query)
                if not res:
                    subject = 'QOS Modem Alert'
                    for name, recipient in QOS_RECIPIENTS:
                        msg = ('Hello %s,\nThere was no response from %s(%s) when using %s!\n\nRegards,\nJenifer')
                        msg = msg % (name, shortcode['identity'], shortcode['name'], modem['name'])
                        send_email('root@uganda.rapidsms.org',recipient, subject, msg)
                        logging.warning("[%s] No response from %s for %s"%('/monitor', shortcode['identity'], modem['name']))
        logging.debug("[%s] Stopped Mornitoring"%('/monitor'))
        return "Done!"

class CheckModems:
    def GET(self):
        try:
            f = urllib.urlopen(KANNEL_STATUS_URL)
            x = f.readlines()
        except IOError, (instance):
            logging.debug("[%s] Checked status: perhaps kannel is down!"%('/check'))
            return "Kannel is likely to be down! Sam is your friend now!"
        p = x[:]

        y = GetBackends(db, 'm', True)
        modem_backends = y.get()
        status = 'offline'
        toret = ""
        smscs = [z['smsc_name'] for z in modem_backends]
        for l in p:
            if not l.strip():
                continue
            for smsc in smscs:
                pattern = re.compile(r'%s'%smsc)
                if pattern.match(l.strip()):
                    status = l.strip().split()[2].replace('(','')
                    toret += "%s is %s\n"%(smsc, status)
        logging.debug("[%s] Checked status for %s"%('/check', smscs))
        return toret

class DisableEnableBackend:
    def get_backendlist(self,l):
        t = ''
        for i in l:
            t += "\'%s\',"%(i)
        return t[:-1]

    def GET(self):
        params = web.input(
                backend_list='',
                username='',
                passwd='',
                action='disable'
                )
        backend_list = params.backend_list
        if not backend_list:
            web.ctx.status = '400 Bad Request'
            return "No Backends Specified for enabling/disabling!"
        if params.action not in ['disable', 'enable']:
            web.ctx.status = '400 Bad Request'
            return "Unknown action %s passed as parameter"%params.action
        backend_list = backend_list.split(',')
        t_query = ("UPDATE backends SET active = %s WHERE smsc_name IN (%s)")
        query = t_query % (False if params.action=='disable' else True,self.get_backendlist(backend_list))
        db.query(query)
        resp = ', '.join(backend_list) + " successfully %s"%('disabled' if params.action == 'disable' else 'enabled')
        logging.debug('[%s] %s the following backends: %s '%('/manage',
            'disabled' if params.action == 'disable' else 'enabled', backend_list))
        return resp

class Info:
    def GET(self):
        return "Not yet Implemented!"

# Consider doing webpy nose testing!!
class Test:
    def GET(self):
        x = GetBackends(db,'s',True)
        shortcode_backends = x.get()
        #print shortcode_backends[0]
        y = GetAllowedModems(db,2)
        #print y.get()[0]
        SendModemAvailabilityAlert('mtn-modem')

        #print SENDSMS_URL
        modems  = GetBackends(db,'m',True).get()
        backend_id = [b['id'] for b in modems if b['name'] == 'mtn-modem']
        #print backend_id
        log_message_dict = {
                'backend_id':backend_id[0],
                'msg_out':'2012-03-18 04',
                'destination':'8500',
                'status_out':'Q'
                }
        with db.transaction():
            log_message(db, log_message_dict)

        return "It works!!"

if __name__ == "__main__":
      app.run()

#makes sure apache wsgi sees our app
application = web.application(urls, globals()).wsgifunc()
