BEGIN;
CREATE TABLE users(
    id  SERIAL NOT NULL PRIMARY KEY,
    firstname TEXT NOT NULL DEFAULT '',
    lastname TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL,
    utype TEXT NOT NULL DEFAULT 'admin',
    active BOOLEAN DEFAULT 't',
    cdate TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE backends(
    id  SERIAL NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    smsc_name TEXT NOT NULL,
    identity TEXT NOT NULL,
    btype TEXT NOT NULL DEFAULT 'm',
    active BOOLEAN DEFAULT 't',
    cdate TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE shortcode_allowed_modems(
    id  SERIAL NOT NULL PRIMARY KEY,
    shortcode_id INTEGER NOT NULL REFERENCES backends ON DELETE CASCADE ON UPDATE CASCADE,
    allowedlist INTEGER[] NOT NULL DEFAULT ARRAY[]::INTEGER[],
    cdate TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ldate TIMESTAMPTZ
);

CREATE TABLE messages(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    backend_id INTEGER NOT NULL REFERENCES backends ON DELETE CASCADE ON UPDATE CASCADE,
    msg_out TEXT NOT NULL DEFAULT '',
    msg_in TEXT NOT NULL DEFAULT '',
    destination TEXT NOT NULL DEFAULT '',
    status_out TEXT NOT NULL,
    cdate TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ldate TIMESTAMPTZ
);

CREATE TABLE misc(
        id SERIAL NOT NULL PRIMARY KEY,
        item TEXT NOT NULL,
        val TEXT DEFAULT '',
        detail TEXT DEFAULT ''
);

CREATE TABLE templates(
        id SERIAL NOT NULL PRIMARY KEY,
        name TEXT NOT NULL,
        en_txt TEXT NOT NULL DEFAULT '',
        fr_txt TEXT NOT NULL DEFAULT '',
        cdate TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Sample data
INSERT INTO users (firstname, lastname, email, utype, active)
VALUES
    ('Samuel','Sekiwere','sekiskylink@gmail.com','admin','t'),
    ('Alfred','Mukasa','asseym@gmail.com','admin','t'),
    ('Victor','Miclovich','vicmiclovich@gmail.com','admin','t'),
    ('James','Powell','js123powell@gmail.com','manager','t'),
    ('Sean','Blaschke','sean.blaschke@gmail.com','manager','t'),
    ('Stefan','Bock','stiefbock@gmail.com','manager','t'),
    ('Terra','Weikel','terraw@gmail.com','manager','f');

INSERT INTO backends (name, smsc_name, identity, btype)
VALUES
    ('test','fake','1234','t'),
    ('dmark6767','dmark','6767','s'),
    ('dmark8500','dmark','8500','s'),
    ('yo6200','yo','6200','s'),
    ('yo8200','yo','8200','s'),
    ('zain6767','zain','6767','s'),
    ('zain8500','zain','8500','s'),
    ('utl6767','utl','6767','s'),
    ('utl8500','utl','8500','s'),
    ('MNT','mtn-modem','256777773260','m'),
    ('UTL','utl-modem','256711957281','m'),
    ('AIRTEL','airtel-modem','256752145316','m'),
    ('WARID','warid-modem','256701205129','m'),
    ('ORANGE','orange-modem','256790403038','m');

INSERT INTO misc (item, val, detail)
VALUES
    ('DEFAULT_EMAIL_SENDER','root@uganda.rapidsms.org','The defaul email sender'),
    ('KANNEL_STATUS_URL','http://localhost:13000/status','The Kannel status URL'),
    ('SENDSMS_URL','http://localhost:13013/cgi-bin/sendsms?username=tester&password=foobar','The Send SMS URL'),
    ('ACTIVATE_MANAGERS','true','Whether to activate managers for email alerts');

INSERT INTO templates(name, en_txt)
VALUES
    ('QOS_SEND_SUBJ','QOS Messages Sent at: '),
    ('QOS_SEND_BODY_LINIE1',E'Hi,\nJennifer sent SMS from the following networks:\nSENDER                         | RECIPIENT\n'),
    ('QOS_SEND_BODY_LINIE2',E'----------------------------------------------\n'),
    ('QOS_SEND_INNER_BODY',E'%s(%s)%s| %s\n'),
    ('QOS_RECV_ALL_SUBJ','QOS Messages Received within:'),
    ('QOS_ALARM_SUBJ','QOS Monitor Alert'),
    ('QOS_RECV_BODY_LINE1',E'Hi,\nJennifer received SMS from all networks:'),
    ('QOS_RECV_BODY_LINE2',E'----------------------------------------------------\n'),
    ('QOS_ALARM_BODY_LINE1',E'Hello %s,\nJenifer didn\'t get a reply for the following networks:\n'),
    ('QOS_ALARM_BODY_LINE2',E'----------------------------------------------------\n'),
    ('QOS_ALARM_INNER_BODY',E'%s(%s) -Tested with %s\n'),
    ('QOS_FOOTER',E'\n\nRegards,\nJennifer'),
    ('QOS_TIME_LINE','Time of Testing: ');

INSERT INTO shortcode_allowed_modems (shortcode_id, allowedlist)
VALUES
    ((SELECT id FROM backends WHERE name='dmark6767'),
        ARRAY[
            (SELECT id FROM backends WHERE name = 'mtn-modem'),
            (SELECT id FROM backends WHERE name = 'warid-modem'),
            (SELECT id FROM backends WHERE name = 'orange-modem')
        ]),
    ((SELECT id FROM backends WHERE name='dmark8500'),
        ARRAY[
            (SELECT id FROM backends WHERE name = 'mtn-modem'),
            (SELECT id FROM backends WHERE name = 'warid-modem'),
            (SELECT id FROM backends WHERE name = 'orange-modem')
        ]),
     ((SELECT id FROM backends WHERE name='yo6200'),
        ARRAY[
            (SELECT id FROM backends WHERE name = 'mtn-modem'),
            (SELECT id FROM backends WHERE name = 'warid-modem'),
            (SELECT id FROM backends WHERE name = 'utl-modem'),
            (SELECT id FROM backends WHERE name = 'orange-modem')
        ]),
     ((SELECT id FROM backends WHERE name='yo8200'),
        ARRAY[
            (SELECT id FROM backends WHERE name = 'mtn-modem'),
            (SELECT id FROM backends WHERE name = 'warid-modem'),
            (SELECT id FROM backends WHERE name = 'orange-modem')
        ]),
    ((SELECT id FROM backends WHERE name='zain6767'),
        ARRAY[
            (SELECT id FROM backends WHERE name = 'airtel-modem')
        ]
    ),
    ((SELECT id FROM backends WHERE name='zain8500'),
        ARRAY[
            (SELECT id FROM backends WHERE name = 'airtel-modem')
        ]
    ),
    ((SELECT id FROM backends WHERE name='utl6767'),
        ARRAY[
            (SELECT id FROM backends WHERE name = 'utl-modem')
        ]
    ),
    ((SELECT id FROM backends WHERE name='utl8500'),
        ARRAY[
            (SELECT id FROM backends WHERE name = 'utl-modem')
        ]
    );

CREATE OR REPLACE FUNCTION array_pop(a anyarray, element character varying)
RETURNS anyarray
LANGUAGE plpgsql
AS $function$
DECLARE
    result a%TYPE;
    BEGIN
        SELECT ARRAY(
                SELECT b.e FROM (SELECT unnest(a)) AS b(e) WHERE b.e <> element) INTO result;
            RETURN result;
        END;
$function$;

CREATE VIEW shortcode_modems AS
    SELECT a.shortcode_id, b.name, a.allowedlist FROM shortcode_allowed_modems a, backends b
    WHERE a.shortcode_id =  b.id;
END;
