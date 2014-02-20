
Submissions
=============

XForms supports three different modes of forms being submitted, via hand entered SMS, via XForm compliant HTTP POSTs, or via our own URL encoded SMS POSTS.  Each form has its own unique format, but each will pass through the same validation and signalling paths.

Manual SMS Submission
---------------------

The creation of an XForm creates a new SMS endpoint for that form.  The form's ``keyword`` will determine the SMS keyword that will trigger handling of said form.  If the form is successfully parsed and all constraints pass, then if set, the ``response`` element for the form will be sent back to the sender of the SMS message.

Note that we choose to be leniant about **extra** fields passed into SMS forms, these will be silently ignored.

Some examples SMS forms and responses for an XForm with the keyword ``survey`` and the required field of ``age`` and optional field of ``name``::

     >> survey +age 10
     << Thank you for submitting a new survey.

     >> survey
     << You are missing the required +age field.

     >> survey +age ten
     << The 'age' field must be an integer.

     >> survey +age 10 +name matt berg
     << Thank you for submitting a new survey.

     >> survey +name matt berg +age 10
     << Thank you for submitting a new survey.

     >> survey +name matt berg +age 10 +city new york
     << Thank you for submitting a new survey.

XForm HTTP Post
---------------

Any forms created will also be made available as standard XForms.  In order to expose your forms through this interface you will need to set the ``XFORMS_HOST`` variable in your ``settings.py`` to the host (and port if not 80) of your RapidSMS Server::

    XFORMS_HOST="rapidsms.unicef.org:8000"

You can download a free ODK Client from the Android market named ``ODK Collect``.  Once installed, just change the server to point to the same host specified above.  You will be able to list, install, and submit the forms you have created on your server using the native Android application.


Endpoints
*********

Two endpoints are implemented in order to work seamlessly with the ODK Collect client:

``/formList``
	Returns an XML document containing an index of all the form definitions installed on the server

``/submission``
	The end point that XForm clients POST their submissions to

Note that these URLs are hard coded in the ODK Collect client, so they cannot be changed.
