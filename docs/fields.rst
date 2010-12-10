
XForm Fields
===========================================

An XForm is composed of one or more ordered fields.  Currently four types are supported for each field, ``integer``, ``decimal``, ``string`` and ``coordinate``.  Each field must have a unique human readable name, as well as a shorter ``slug`` used to uniquely identify it.  You may also specify help text that will be displayed in rich XForm clients.


Integer Field
--------------

An integer field which contains even numbers.

Examples::
	
	survey +age 20
	survey +height 35

Decimal Field
--------------

A decimal field holds a real, non integer number.  It has a maximum precision of 9 digits before and 9 digits after the period.

Examples::
	
	survey +flow 5.4
	survey +temp 98.6

String Field
------------

A string field, represents just a block of text.

Examples::
	
	survey +name matt berg
	survey +comment well is in need of repair

Coordinate Field
----------------

A coordinate field, which in practice is a pairing of decimal fields.

Examples::

	survey +loc 1.4564 1.5435
	survey +track 1.5456 1.2355

Custom Field Types
------------------

You can also create custom field types, which can point either to your own domain objects or which just do specialized parsing before storing the value as a primitive.

You can register fields using the ``register_field_type`` static method in XFormField.  The Coordinate (geopoint) field is actually implemented in this way, using the following code::

    def create_geopoint(command, value):
        """
        Used by our arbitrary field saving / lookup.  This takes the command and the string value representing
        a geolocation and returns a Point location.
        """
        coords = value.split(' ')
        if len(coords) < 2:
           raise ValidationError("+%s parameter must be GPS coordinates in the format 'lat long'" % command)

        for coord in coords[0:2]:
            try:
                test = float(coord)
            except ValueError:
                raise ValidationError("+%s parameter must be GPS coordinates the format 'lat long'" % command)
        
        # lat needs to be between -90 and 90
        if float(coords[0]) < -90 or float(coords[0]) > 90:
            raise ValidationError("+%s parameter has invalid latitude, must be between -90 and 90" % command)
        
        # lng needs to be between -180 and 180
        if float(coords[1]) < -180 or float(coords[1]) > 180:
            raise ValidationError("+%s parameter has invalid longitude, must be between -180 and 180" % command)

        # our cleaned value is the coordinates as a tuple
        cleaned_value = Point.objects.create(latitude=coords[0], longitude=coords[1])
        return cleaned_value

    # register geopoints as a type
    XFormField.register_field_type(XFormField.TYPE_GEOPOINT, 'GPS Coordinate', create_geopoint,
                                   xforms_type='geopoint', db_type=XFormField.TYPE_OBJECT)


Alternatively, you could create a new field type to deal with custom formats.  The following is an example of a custom 'timespan' field which parses time values in formats like '1day' or '6 months', but stores the value in an ordinary integer field representing the number of days::

        def parse_timespan(command, value):
            """
            Parses a timespan object in the format '5days' or '6 months', returning the value as an integer
            of the number of days represented by that timespan.
            """
            match = re.match("(\d+)\W*months?", value, re.IGNORECASE)
            if match:
                return int(match.group(1))*30
            match = re.match("(\d+)\W*days?", value, re.IGNORECASE)
            if match:
                return int(match.group(1))

            raise ValidationError("%s parameter value of '%s' is not a valid timespan." % (command, value))

        XFormField.register_field_type('timespan', 'Timespan', parse_timespan, 
                                       xforms_type='string', db_type=XFormField.TYPE_INT)



Field Constraints
==================

Every field can have one or more ordered constraints applied to it.  For each constraint you can specify a custom error message that is returned if the constraint fails.

The types of constraints are:

``required``
	a non empty value is required for all form submission

``min_value``
	The numeric value of the field must be n or greater.

``max_value``
	The numeric value of the field must be n or less.

``min_len``
	The value as a string must be be at least of length n

``max_len``
	The value as a string must be at most of length n

``regex``
	The value must match the passed in regex.  You likely want to include anchor tokens if the regular expression is meant to be inclusive.

Some example regular expressions::
	
	# only matches the strings 'mal', 'fev' or 'shi'
	^(mal|fev|shi)$

	# matches phone numbers in the form 333-3333
	^\d\d\d-\d\d\d\d$

	# forces the string to be only lowercase letters
	^[a-z]+$


