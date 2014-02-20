
Security
=============

XForms supports a few different ways to restrict access to who can view and submit form data.  Individual forms can be restricted to the users in one or more Django user groups.  If set, then XForms will only allow submissions by members of said group.

The mechanism for authenticating users depends on how they are submitting data, whether that be through the ODK Client's standard HTTP interface or via SMS.

ODK Client Authentication
--------------------------

ODK Client 1.1.7 and later support standard HTTP digest authentication.  The user can set the username and password within the client before starting to interact with the server.  XForms will only ask for authentication credentials if the ``AUTHENTICATE_XFORMS`` variable in ``settings.py`` is set to ``True``.

Only users who have valid user credentials will be able to view which forms are available on the server.  Additionally, the list of forms available will be filtered according to the group membership of the user and the restrictions based on each form.

At the time of submission, the same authentication will be done, verifying that the client has valid credentials and that that user has permission to add data for that form.

Note that although digest authentication is secure in that the user's password is never sent across the wire in plaintext, the digest itself can easily be sniffed and used for subsequent submissions by an attacker.  Therefore the security of the system is only as secure as the network.  If true security is required, then the server should be running on an https port.

Compatability
~~~~~~~~~~~~~~

Note that the ``django-digest`` library which XForms uses to do digest authentication does not work correctly when using the SQLite backend.  You **must** use MySQL or PostgreSQL as a backend in order to use digest authentication.

SMS Authentication
-------------------

Authenticating requests via SMS is done using Django Profile objects.  Whatever object is used as the Profile object must define a class method ``lookup_by_connection`` which given a RapidSMS Connection object returns either ``None`` or the Profile instance related to that Connection.

XForms then uses that Profile and its associated User object to check the user's permission to the form.

If a user is found not to have permission to use the form, then the submissions is marked as having an error, and the user is sent the error message set within the form.

Customization
--------------

Some installations may wish to customize either the method for looking up users, or the mechanism used to check whether a User has permissions to a particular XForm.  XForms provides two hooks to customize these behaviors.

XFORMS_USER_LOOKUP
~~~~~~~~~~~~~~~~~~~

This setting in settings.py should be the name of a method which when given a RapidSMS Connection object will return a Django User object or ``None``.

The default implementation can be found in ``models.py``, named ``profile_connection_lookup``, which uses the mechanism detailed above to map Profile objects to Connections.

XFORMS_AUTHENTICATION_CHECKER
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This setting in settings.py allows installations to customize how a User is determined to have access to an XForm instance.  The method defined will be passed User and XForm instance, and is expected to return ``True`` if the User can access the form and ``False`` otherwise.

This method will be used by both ODK clients to filter lists and restrict access as well as by SMS submissions.

The default implementation can be found in ``models.py``, named ``can_user_use_form``, which simply checks that the user is a member of the groups that a form is restricted to.
