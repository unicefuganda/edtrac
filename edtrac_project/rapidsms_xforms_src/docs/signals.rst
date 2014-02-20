
Signals
===========================================

The XForms app uses signals to let you integrate with incoming submissions.  You can choose to listen for submissions as they come in.  You should make every effort to integrate your application in this way instead of changing the XForms app itself.  We consider it an error in our own design if you are modifying the XForms source, so please let us know if that is the case.


xform_received Signal
---------------------------

Every time a new XForm submission comes in, a signal will be triggered for that submission.  The listener will receive a dict containing two values, ``submission``, the actual XFormSubmission object, and ``xform`` the XForm type that was submitted.

Note that all submissions will trigger a signal.  It is up to the caller to filter the incoming submissions based on whether they were successful or are the type of XForm the listener is interested in.

An example of a simple listener::

    from xforms.models import xform_received

    # define a listener
    def handle_submission(sender, **args):
    	submission = args['submission']
        xform = args['xform']

	if xform.keyword == 'survey' && not submission.has_errors:
	   .. do your own logic here ..

    # then wire it to the xform_received signal
    xform_received.connect(handle_submission)

Note that you can alter the response sent to the user by changing the ``response`` attribute in the passed in submission.  This can be used to return more custom responses to incoming messages.

Submission Editing
------------------

Note that the ``xform_received`` signal will also be sent when an administrator edits and saves a submission.  As a listener you need to manage that an incomiung signal may be for a submission you have seen before.

