
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


