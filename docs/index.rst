.. rapidsms-xforms documentation master file, created by
   sphinx-quickstart on Thu Jun 10 14:21:09 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Introduction
===========================================

The RapidSMS xforms application provides an interactive web based form builder.  Created forms support data being submitted to them via freehand formatted SMS, standard XForm HTTP posts or structured SMS.  Applications can choose to use xforms to quickly prototype systems, or even use them as their primary interface, using Django signals to perform more complicated logic on new submissions.

- Interactive Web UI to build Forms
- Flexible constraint architecture to allow for validation of inputs with customized error messaging
- Ability to submit forms either via hand entered SMS's or via HTTP Posts in XForm format
- Display of submitted forms and editing of values by admin
- Signal architecture to allow you to plug in your own handler for submitted forms
- Integration with ODK Collect, an Android XForms client

The full documentation can be found at:
  http://nyaruka.github.com/rapidsms-xforms

The official source code repository is:
  http://www.github.com/nyaruka/rapidsms-xforms

A little video showing this app in use:
  http://www.youtube.com/watch?v=PyjEruT5uoU

Built by Nyaruka Ltd under contract of UNICEF:
  http://www.nyaruka.com

Installation From Cheese Shop
===========================================

You can install the latest version of the rapidsms-xforms library straight from the cheese shop::

   % pip install rapidsms-xforms

You'll also need to install django-eav from GitHub, which isn't in PyPi just yet::

   % pip install -e git+http://github.com/mvpdev/django-eav.git#egg=django-eav

Installation From Github
===========================================

You can always get the latest version of rapidsms-xforms from github.  Note that the tip of the repo is not guaranteed to be stable.  You should use the verison available via pip unless you have a specific reason not to.

You can install the requirements using the ``pip-requires.txt`` file::

   % pip install -r pip-requires.txt

Configuration
==============

To enable XForms for your project, edit your ``settings.py`` to add ``rapidsms_xforms``, ``eav`` and ``uni_form``::

  INSTALLED_APPS = ( "rapidsms",
   		       .. other apps ..
                     "eav",
  		     "uni_form",
  		     "rapidsms_xforms" )

You will probably also want to add XForms as one of the main RapidSMS tabs::

   RAPIDSMS_TABS = [
     ('rapidsms.views.dashboard', 'Dashboard'),	
         .. other tabs ..
     ('xforms', 'XForms')
   ]

While you are in ``settings.py`` might as well change your ``LOGIN_URL`` to match RapidSMS's::

   # set our login url to match RapidSMS's url patterns
   LOGIN_URL = "/account/login"

Finally, include the XForms urls in your project's urls.py::

   urlpatterns = patterns('',
      .. other url patterns ..
      ('', include('rapidsms_xforms.urls'))
   )

If you are going to use XForms with ODK Collect or another XForms client, you need to specify your host in you settings as well::

   XFORMS_HOST = 'www.rapidsms-server.com'

Finally sync your database with::

   % python manage.py syncdb

Once you restart RapidSMS a new tab will created letting you create, manage and view forms and their submissions.


Building the Documentation
==========================

XForms is fully documented.  To build the html docs, go to the /docs subdirectory and execute::
       
       % make html

The final docs will be found in ``docs/_build/html/index.html``


Updating Github Docs
====================

We use some modified paver scripts fromthe github-tools package to manage uploading our built docs to github::

    % easy_install github-tools[template]
    % rm -rf docs/_build
    % paver gh_pages_build gh_pages_update -m "update github docs"

Running the Tests
=================

We use the excellent ``django-test-extensions`` package to give us coverage reports for our unit tests.  This let's us guarantee that we have 100% coverage for our tests. (not the same as saying there are no bugs, but a start)

If you want to run our tests with coverage, you'll need to install django-test-extensions::

   % pip install django-test-extensions

And edit your ``INSTALLED_APPS`` in ``settings.py`` to include django-test-extensions::
    
  INSTALLED_APPS = ( "rapidsms",
  		     "django-test-extensions",
  		     "rapidsms_xforms" )

You'll then be able to run the unit tests and get a full coverage report::

       % ./manage.py test rapidsms_xforms --coverage       

NOTE: There is currently an issue in django-test-extensions that makes all module level elements (imports and the like) show up as non-covered.  We are trying to get to the bottom of this with the author.

Getting Started
===========================================

Once installed, click on the XForms tab.  Here you can create a new form.  A form represents a new SMS (or XForm) endpoint, allowing users enter data into the system according to the fields you have defined.  Try creating a new form, naving it ``survey`` and add one integer field named ``age`` and a string field named ``name``.

Once saved you can submit SMS messages to the system in the forms::

     survey +age 10 +name emily
     survey + age 30   +name monty python
     survey +name eric +age 15.4

You can view submitted reports after they come in, and edit them as you like.

Now try experimenting with adding restrictions to the fields, whether they are required, their min and max values etc..  You'll find you can easily customize the error messages as they come in.

You can also submit surveys using an XForms client, like ODK Collect.  The XForms application adds the appropriate endpoints to both discover available forms, download them to the device, and submit them to the server.  This makes RapidSMS a full XForms endpoint for simple forms, giving you the choice as to whether to submit via a rich XForms client or via SMS.

Contents:
===========================================

.. toctree::
   :maxdepth: 2

   fields
   signals
   submissions
   security

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

