#!/usr/bin/python
# -*- coding: utf8 -*-
# Author: Samuel Sekiwere <sekiskylink@gmail.com>

import web
import urllib
import httplib
import logging
import psycopg2
import re
import time
from datetime import datetime
from datetime import timedelta
from urllib import urlencode
from urllib import urlopen

class AppURLopener(urllib.FancyURLopener):
	version = "QOS /0.1"

urllib._urlopener = AppURLopener()

render = web.template.render('/var/www/qos')

logging.basicConfig( format='%(asctime)s:%(levelname)s:%(message)s', filename='/var/log/jennifer/jennifer.log',
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
        "/manage_shortcode", "ManageShortcode",
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

SETTINGS = {
    'SENDSMS_URL': 'http://localhost:13013/cgi-bin/sendsms?username=tester&password=foobar',
    'DEFAULT_EMAIL_SENDER': 'root@uganda.rapidsms.org',
    'KANNEL_STATUS_URL': 'http://localhost:13000/status',
    'LANGUAGE': 'en',
    }
TEMPLATES = {
            'QOS_SEND_SUBJ':'QOS Messages Sent at: ',
            'QOS_SEND_BODY_LINIE1':'Hi,\nJennifer sent SMS from the following networks:\nSENDER                         | RECIPIENT\n',
            'QOS_SEND_INNER_BODY':'%s(%s)%s| %s\n',
            'QOS_RECV_ALL_SUBJ':'QOS Messages Received within:',
            'QOS_ALARM_SUBJ':'QOS Monitor Alert at: %s',
            'QOS_RECV_BODY_LINE1':'Hi,\nWoooooow!!!\nJennifer received SMS from all networks:',
            'QOS_RECV_BODY_LINE2':'----------------------------------------------------\n',
            'QOS_ALARM_BODY_LINE1':'Hello %s,\nJenifer didn\'t get a reply for the following networks:\n',
            'QOS_ALARM_INNER_BODY':'%s -Tested with %s(%s)\n',
            'QOS_FOOTER':'\n\nRegards,\nJennifer',
            'QOS_TIME_LINE':'Time of Testing: ',
        }
QOS_INTERVAL = {'hours':1, 'minutes':0, 'offset':5}
## Helper Classes and Functions
class GetBackends(object):
    """Returns backends of a given type"""
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
    """Given a shortcode, return modems allowed to send to shortcode"""
    def __init__(self,db,shortcode_id):
        self.db = db
        self.shortcode_id = shortcode_id
    def get(self):
        t_query = ("SELECT id, name, identity, smsc_name, active FROM backends "
                    "WHERE id IN (SELECT unnest(allowedlist) FROM shortcode_allowed_modems WHERE shortcode_id = %s) AND active = %s")
        query = t_query % (self.shortcode_id, True)
        res = self.db.query(query)
        return res

def IsModemActive(modem_smscname):
    """Checks modem status in Kannel i.e(online, re-connecting,..)"""
    try:
        f = urllib.urlopen(SETTINGS['KANNEL_STATUS_URL'])
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

class Settings(object):
    """Load settings from misc table in DB"""
    def __init__(self,db):
        self.db = db
        self.get_all_setting()
        self.get_email_recipients()
        self.get_templates()
    def get_all_setting(self):
        global SETTINGS
        res = self.db.query("SELECT item,val FROM misc")
        if res:
            for setting in res:
                SETTINGS['%s'%setting['item']] = setting['val']
    def get_email_recipients(self):
        global QOS_RECIPIENTS, SETTINGS
        res = self.db.query("SELECT firstname, email, utype FROM users WHERE active = %s"%True)
        if res:
            for r in res:
                if r['utype'] == 'admin':
                    QOS_RECIPIENTS.append((r['firstname'],r['email']))
                else:
                    if 'ACTIVATE_MANAGERS' in SETTINGS:
                        if SETTINGS['ACTIVATE_MANAGERS'] == 'true':
                            QOS_RECIPIENTS.append((r['firstname'],r['email']))
        QOS_RECIPIENTS = list(set(QOS_RECIPIENTS))
    def get_templates(self):
        global TEMPLATES
        res =  self.db.query('SELECT name, en_txt, fr_txt FROM templates')
        if res:
            for template in res:
                TEMPLATES['%s'%template['name']] = template['%s'%('%s_txt'%getattr(SETTINGS,'LANGUAGE','en'))]


# Load Settings from DB
Settings(db)

def sendsms(frm, to, msg,smsc):
    """sends the sms"""
    params = {'from':frm,'to':to,'text':msg,'smsc':smsc}
    surl = SETTINGS['SENDSMS_URL']
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
    """Log sent message to messages table"""
    dbconn.insert('messages',backend_id=msg_dict['backend_id'], msg_out=msg_dict['msg_out'],
            status_out=msg_dict['status_out'], destination=msg_dict['destination'])


def send_email(_from, recipient, subject, msg):
    """Sends email"""
    web.sendmail(_from,recipient, subject, msg)

def SendModemAvailabilityAlert(modem_smscname):
    """used to send mail if modem is not onlile"""
    subject = 'QOS Modem Alert'
    for name, email in MODEM_STATUS_RECIPIENTS:
        msg = 'Hello %s,\nThe %s is not on-line!\n\nRegards,\nJenifer'%(name, modem_smscname)
        send_email(SETTINGS['DEFAULT_EMAIL_SENDER'], email, subject, msg)

def get_qos_time_offset():
    qos_interval = QOS_INTERVAL
    time_offset = datetime.now() - timedelta(hours=qos_interval['hours'],
                    minutes=(qos_interval['minutes'] + qos_interval['offset']))
    return time_offset

def get_backendlist(l,ret_strlist=True):
    """return list to pass to IN in an SQL query. Eg [1,2,3] returns 1,2,3"""
    t = ''
    for i in l:
        if ret_strlist:
            t += "\'%s\',"%(i)
        else:
            t += "%s,"%(i)
    return t[:-1]

#Page Handlers
class HandleReceivedQosMessage:
    """This is what Kannel get-url calls"""
    def GET(self):
        params = web.input(
                sender='',
                receiver='',
                backend='',
                message=''
                )
        web.header("Content-Type","text/plain; charset=utf-8");
        x = GetBackends(db, 's', True)
        shortcode_backends = x.get()
        shortcodes = [s['identity'] for s in shortcode_backends]
        params.sender = params.sender.replace('+','')
        if params.sender.lower() not in shortcodes:
            return "Ignored, black listed sender!"
        msg = params.message.strip()
        if not re.match(r'^\d{4}-\d{2}-\d{2}\s\d{2}$', msg):
            return "Message not in format we want!"
        # Now log message to DB in msg_in
        modems  = GetBackends(db, 'm' ,True).get()
        modem_numbers = [m['identity'] for m in GetBackends(db, 'm', True).get()]
        params.receiver = params.receiver.replace('+','')
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
    """handles DLRs"""
    def GET(self):
        params = web.input(
                source='',
                destination='',
                message='',
                dlrvalue=''
                )
        web.header("Content-Type","text/plain; charset=utf-8");
        return "It works!"

class SendQosMessages:
    """Sends the QOS messages"""
    def GET(self):
        params = web.input()
        web.header("Content-Type","text/plain; charset=utf-8");
        x = GetBackends(db,'s',True)
        shortcode_backends = x.get()
        applied_modems = [] # for logging
        failed_modems = []
        logging.debug("[%s] Started Sending QOS Messages"%('/send'))
        testing_time = datetime.now().strftime('%H:%M%p %h %d, %Y')
        rpt_subject = "%s: %s"%(TEMPLATES['QOS_SEND_SUBJ'],datetime.now().strftime('%Y-%m-%d %H'))
        rpt_body = TEMPLATES['QOS_SEND_BODY_LINIE1']
        rpt_body += TEMPLATES['QOS_SEND_BODY_LINIE2']
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
                msg = datetime.now().strftime('%Y-%m-%d %H')
                _from = modem['identity']
                to = shortcode['identity']
                smsc = modem['smsc_name']
                applied_modems.append(smsc)
                res = sendsms(_from, to, msg, smsc)
                if isinstance(res,list):
                    res = ' '.join(res)
                if res.find('Accept') <> -1:
                    status = 'S'
                elif res.find('Error') <> -1:
                    status = 'E'
                else:
                    status = 'Q'
                if status == 'E':
                    email_body = 'Hi,\nError sending from %s to %s.\n\nRegards,\nJennifer'%(modem['name'],shortcode['identity'])
                    send_email(SETTINGS['DEFAULT_EMAIL_SENDER'], 'sekiskylink@gmail.com', "Send SMS Error",email_body)
                rpt_body += TEMPLATES['QOS_SEND_INNER_BODY'] %(modem['name'], modem['identity'],
                        ' '*(32-(len(modem['name']+ modem['identity'])+2)),shortcode['identity'])
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
                logging.debug("[%s] Sent SMS [SMSC: %s] [from: %s] [to: %s] [msg: %s]"%('/send',
                    modem['smsc_name'], modem['identity'], shortcode['identity'], msg))
        logging.debug("[%s] Sent QOS messages using %s: Failed = %s"%('/send', list(set(applied_modems)), list(set(failed_modems))))
        rpt_body += "\n%s %s\n"%(TEMPLATES['QOS_TIME_LINE'],testing_time) + TEMPLATES['QOS_FOOTER']
        send_email(SETTINGS['DEFAULT_EMAIL_SENDER'], [email for name,email in QOS_RECIPIENTS], rpt_subject, rpt_body)
        return "Done!"

class MonitorQosMessages:
    """Used to monitor sent QOS messages. did recipient receive and respond?"""
    def GET(self):
        params = web.input()
        web.header("Content-Type","text/plain; charset=utf-8");
        x = GetBackends(db,'s',True)
        shortcode_backends = x.get()
        time_offset = get_qos_time_offset()
        testing_time = datetime.now().strftime('%H:%M%p %h %d, %Y')
        logging.debug("[%s] Started Mornitoring"%('/monitor'))
        rpt_subject = "%s %s"%(TEMPLATES['QOS_RECV_ALL_SUBJ'],datetime.now().strftime('%Y-%m-%d %H'))
        rpt_body = TEMPLATES['QOS_RECV_BODY_LINE1']
        rpt_body += TEMPLATES['QOS_RECV_BODY_LINE2']
        rpt_body2 = ""
        subject = TEMPLATES['QOS_ALARM_SUBJ'] % time.strftime('%F %H')
        monitor_msg = ('Hello %s,\nJenifer didn\'t get a reply for the following networks:\n')
        monitor_msg +=("----------------------------------------------------\n")
        there_is_an_alert = False
        for shortcode in shortcode_backends:
            y = GetAllowedModems(db, shortcode['id'])
            allowed_modems = y.get()
            for modem in allowed_modems:
                t_query = ("SELECT id FROM messages WHERE cdate > '%s' AND msg_out = msg_in AND msg_out <> '' "
                            " AND backend_id = %s AND destination = '%s'")
                query = t_query % (time_offset, modem['id'], shortcode['identity'])
                res = db.query(query)
                #check if message was previously sent successfully from modem
                t_query = ("SELECT id FROM messages WHERE msg_out = '%s' AND backend_id = %s AND status_out = '%s'")
                res_sent = db.query(t_query % (time.strftime('%F %H'), modem['id'], 'S'))

                if not res:
                    if res_sent:
                        there_is_an_alert = True
                        monitor_msg += TEMPLATES['QOS_ALARM_INNER_BODY'] %(modem['name']+(' '*(9-len(modem['name']))), shortcode['identity'], shortcode['smsc_name'])
                        logging.warning("[%s] No response from %s for %s"%('/monitor', shortcode['identity'], modem['name']))
                    else:
                        # modem was down
                        pass
                else:
                    rpt_body2 += TEMPLATES['QOS_ALARM_INNER_BODY'] %(modem['name'], shortcode['identity'],shortcode['smsc_name'])

        if there_is_an_alert:
            for name, recipient in QOS_RECIPIENTS:
                the_msg = (monitor_msg % name) + "\n%s %s\n"%(TEMPLATES['QOS_TIME_LINE'],testing_time) + TEMPLATES['QOS_FOOTER']
                send_email(SETTINGS['DEFAULT_EMAIL_SENDER'],recipient, subject, the_msg)
        else:
            rpt_body += rpt_body2 + "\n%s %s\n"%(TEMPLATES['QOS_TIME_LINE'],testing_time) + TEMPLATES['QOS_FOOTER']
            send_email(SETTINGS['DEFAULT_EMAIL_SENDER'], [email for name,email in QOS_RECIPIENTS], rpt_subject, rpt_body)
        logging.debug("[%s] Stopped Mornitoring"%('/monitor'))
        return "Done!"

class CheckModems:
    """Checks Kannel status of all modems"""
    def GET(self):
        try:
            f = urllib.urlopen(SETTINGS['KANNEL_STATUS_URL'])
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
    """Disable or enable a given backend"""
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
        web.header("Content-Type","text/plain; charset=utf-8");
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

class ManageShortcode:
    """Sets enabled list of modems for a given shortcode"""
    def GET(self):
        params = web.input(
                shortcode_name = '',
                modem_list='',
                )
        web.header("Content-Type","text/plain; charset=utf-8");
        shortcode_name = params.shortcode_name
        modem_list = params.modem_list

        if not modem_list:
            web.ctx.status = '400 Bad Request'
            return "No Modems Specified for enabling/disabling, required parameter: modem_list"
        if not shortcode_name:
            web.ctx.status = '400 Bad Request'
            return "No Shortcode specifies, please pass required parameter: shortcode_name"

        modem_list = modem_list.split(',')
        res = db.query("SELECT id FROM backends WHERE name IN (%s)"%get_backendlist(modem_list,True))
        if not res:
            web.ctx.status = '400 Bad Request'
            return "Specified modem(s) %s not in our list of modems"%modem_list
        shortcode = db.query("SELECT id FROM backends WHERE name = '%s' AND btype = 's'"%(shortcode_name))
        if shortcode:
            shortcode_id = shortcode[0]['id']
        else:
            web.ctx.status = '400 Bad Request'
            return "Unknown Shortcode name %s"%shortcode_name
        modem_ids = [i['id'] for i in res]
        t_query = ("UPDATE shortcode_allowed_modems SET allowedlist = ARRAY[%s] WHERE shortcode_id = %s")
        db.query(t_query % (get_backendlist(modem_ids,False),shortcode_id))
        resp = ', '.join(modem_list) + " successfully set as allowed modems for %s"%(shortcode_name)
        logging.debug('[%s] set [%s] as allowed modems for [%s] '%('/manage_shortcode', ', '.join(modem_list), shortcode_name))
        return "Done!"

class Info:
    """To return some info about system"""
    def GET(self):
        return "Not yet Implemented!"

# Consider doing webpy nose testing!!
class Test:
    """Used for Testing"""
    def GET(self):
        params = web.input()
        web.header("Content-Type","text/plain; charset=utf-8");
        x = GetBackends(db,'s',True)
        shortcode_backends = x.get()
        y = GetAllowedModems(db,2)
        #SendModemAvailabilityAlert('mtn-modem')

        modems  = GetBackends(db,'m',True).get()
        backend_id = [b['id'] for b in modems if b['name'] == 'mtn-modem']
        #log_message_dict = {
        #        'backend_id':backend_id[0],
        #        'msg_out':'2012-03-18 04',
        #        'destination':'8500',
        #        'status_out':'Q'
        #        }
        #with db.transaction():
        #    log_message(db, log_message_dict)
        #sendsms()

        return "It works!!"

if __name__ == "__main__":
      app.run()

#makes sure apache wsgi sees our app
application = web.application(urls, globals()).wsgifunc()
