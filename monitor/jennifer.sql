BEGIN;
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

-- Sample data
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
    ('mtn-modem','mtn-modem','256777773260','m'),
    ('utl-modem','utl-modem','256711957281','m'),
    ('airtel-modem','airtel-modem','256752145316','m'),
    ('warid-modem','warid-modem','256701205129','m'),
    ('orange-modem','orange-modem','256790403038','m');
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
END;
