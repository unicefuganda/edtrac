.. rapidsms-xforms documentation master file, created by
   sphinx-quickstart on Thu Jun 10 14:21:09 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Introduction
===========================================

The RapidSMS xforms application provides an interactive web based form builder.  Created forms support data being submitted to them via freehand formatted SMS, standard XForm HTTP posts or structured SMS.  Applications can choose to use xforms to quickly prototype systems, or even use them as their primary interface, using Django signals to perform more complicated logic on new submissions.

Distinct features:

- Interactive Web UI to build new incoming Forms
- Ability to submit forms via hand entered SMS's, HTTP Posts in XForm format or urlencoded XForm SMSes
- Display of submitted forms and editing of values by admin
- Signal architecture to allow you to plug in your own handler for submitted forms

Installation
===========================================
To use, just put the ``xforms`` on your Python path, then edit your ``settings.py`` to include ``xforms``:

.. sourcecode:: python

  INSTALLED_APPS = ( "rapidsms",
  		     "xforms" )

Then sync your database with ``./manage.py syncdb``.

Once you restart RapidSMS a new tab will created letting you create, manage and view forms and their submissions.

Building the Documentation
==========================

XForms is fully documented.  To build the html docs, go to the /docs subdirectory and execute::
       
       % make html

The final docs will be found in ``docs/_build/html/index.html``

Running the Tests
=================

We use the excellent ``django-test-extensions`` package to give us coverage reports for our unit tests.  This let's us guarantee that we have 100% coverage for our tests. (not the same as saying there are no bugs, but a start)

If you want to run our tests with coverage, you'll need to install django-test-extensions::

   % pip install django-test-extensions

And edit your ``INSTALLED_APPS`` in ``settings.py`` to include django-test-extensions::
    
  INSTALLED_APPS = ( "rapidsms",
  		     "django-test-extensions",
  		     "xforms" )

You'll then be able to run the unit tests and get a full coverage report::

       % ./manage.py test xforms --coverage       

NOTE: There is currently an issue in django-test-extensions that makes all module level elements (imports and the like) show up as non-covered.  We are trying to get to the bottom of this with the author.

Getting Started
===========================================

Once installed, click on the XForms tab.  Here you can create a new form.  A form represents a new SMS (or XForm) endpoint, allowing users enter data into the system according to the fields you have defined.  Try creating a new form, naving it ``survey`` and add one integer field named ``age`` and a string field named ``name``.

Once saved you can submit SMS messages to the system in the forms::

     survey +age 10 +name emily
     survey + age 30   +name greg linden
     survey +name eric +age 15.4

You can view submitted reports after they come in, and edit them as you like.

Now try experimenting with adding restrictions to the fields, whether they are required, their min and max values etc..  You'll find you can easily customize the error messages as they come in.

You can also submit surveys using an XForms client.  From the XForm detail page, just click on the ``download specification`` link to get an XForm compliant view of the XForm.  By default forms will be submitted using HTTP POSTs, but if you are using our modified ODK client you will also be able to submit via SMS.

Contents:
===========================================

.. toctree::
   :maxdepth: 2

   fields
   signals
   submissions

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

