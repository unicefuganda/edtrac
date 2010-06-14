
XForm Fields
===========================================

An XForm is composed of one or more ordered fields.  Currently four types are supported for each field, ``integer``, ``decimal``, ``string`` and ``coordinate``.  Each field must have a unique human readable name, as well as a shorter ``slug`` used to uniquely identify it.  You may also specify help text that will be displayed in rich XForm clients.


Integer Field
--------------

An integer field holds integers.  It supports the following restraints:

``required``
	a value is required for all form submission

``min_value``
	The value must be be at least equal to the test value

``max_value``
	The value must be less than or equal to the test value

Decimal Field
--------------

A decimal field holds a real, non integer number.  It has a maximum precision of 9 digits before and 9 digits after the period.

``required``
	a value is required for all form submission

``min_value``
	The value must be be at least equal to the test value

``max_value``
	The value must be less than or equal to the test value

String Field
------------

A string field, represents just a block of text.

``required``
	a value is required for all form submission

``min_len``
	The value must be be at least of length n

``max_len``
	The value must be at most of length n

``regex``
	The value must match the passed in regex.  This can have multiple forms and should include anchor tokens if the regular expression is meant to be inclusive, some examples::

	^(mal|fev|shi)$

Coordinate Field
----------------

A coordinate field, which in practice is a pairing of decimal fields.



