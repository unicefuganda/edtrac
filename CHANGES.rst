
Version History
===============

Many thanks to everyone who submits pull requests.  We'll merge in most changes that are unit tested and well thought out.

0.3.4
-----
 - nicpottier: nail down version for django-uniform and django
 - nicpottier: fix bug with new version of django-uniform

0.3.3
-----
 - daveycrockett: for string fields which are last in an SMS, use all values, not just the first word
 - daveycrockett: add fix for optional string fields not failing when no value provided, ie: +epi ma
 - daveycrockett: add fix for duplicate optional fields not causing errors, ie: +epi ma 10 ma 12
 - nicpottier: add CHANGES.rst

0.3.2
-----
 - nicpottier: fix bug where messages containing only the keyword were not matching forms
