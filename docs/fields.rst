
XForm Fields
===========================================

An XForm is composed of one or more ordered fields.  Currently four types are supported for each field, ``integer``, ``decimal``, ``string`` and ``coordinate``.  Each field must have a unique human readable name, as well as a shorter ``slug`` used to uniquely identify it.  You may also specify help text that will be displayed in rich XForm clients.


Integer Field
--------------

An integer field holds integers.  It has the following options:

Decimal Field
--------------

A decimal field holds a real, non integer number.  It has a maximum precision of 9 digits before and 9 digits after the period.

Boolean Field
-------------

A boolean field, represents either true or false.  The value can be specified via SMS by any of of ``Y``, ``N``, ``T`` or ``F``.


String Field
------------

A string field, represents just a block of text.

Coordinate Field
----------------

A coordinate field, which in practice is a pairing of decimal fields.



