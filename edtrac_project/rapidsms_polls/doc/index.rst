.. RapidSMS-Polls documentation master file, created by
   sphinx-quickstart on Mon Nov 22 20:20:58 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Introduction
==========================================
The RapidSMS polling application provides a mechanism for collecting an individual piece of data at a time, via SMS, from a potentially large, untrained set of end users.  The goal here is to provide the opposite end of the spectrum to smaller-scale, structure data gathering via SMS, which typically requires a high training budget.  Polling offers the ability to ask a single question, phrased carefully, to which the complete contents of the response message can be used as meaningful data.

poll types
==========
There are 5 types of polls:
 - Free-form: the simplest form, all answers are considered to be free-form text, responses to a completely open-ended question.
 - Yes/No: the content of the message is expected to begin with a 'yes' or a 'no'
 - Numeric Response: the entire content of the message should be a number
 - Registration Based: the question should be phrased as something similar to 'what is your name?' responses will have the option of being tagged to the responding contact's name.
 - Location Based: the responses will be fuzzy matched to existing location names, or new locations will be created.  The locations can also be optionally registered as the reporting location of the contact who submitted the response (for use in mapping other poll responses).

features
========
In addition to the basic poll types, any text-based poll can also add categories: responses fitting a particular category's rules will automatically be applied to this category (and custom responses can be returned based on categorization).  This allows for more complicated keywording for free-form and yes/no polls.

extensions to existing models
=============================
The polling app extends the Contact model by adding the column 'reporting_location', a foreign key to an Area object

dependencies
============
The polling app depends on:
 - eav: (github.com:/mvpdev/django-eav.git)
 - simple_locations: (github.com/yeleman/simple_locations.git)

enhancements
=============
Currently, to keep the polling app light, the more complicated visualizations are not inside the poll application itself, only the admin functionality is.  The visualizations currently sit in the ureport application (github.com/daveycrockett/rapidsms-ureport).  These include a tag cloud, pie charts (by category), histograms (for numeric polls), and maps.

usage
=====
Then to use xforms, edit your ``settings.py`` to add ``poll`` and ``uni_form``::

  INSTALLED_APPS = ( "rapidsms",
   		       .. other apps ..
  		     "uni_form",
  		     "poll" )

You will probably also want to add XForms as one of the main RapidSMS tabs::

  TABS = [
    ('rapidsms.views.dashboard', 'Dashboard'),	
        .. other tabs ..
    ('polls', 'Polls'),
  ]

Finally sync your database with::

    % python manage.py syncdb




Contents:

.. toctree::
   :maxdepth: 2

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

