
Signals
===========================================

The XForms app uses signals to let you integrate with incoming submissions.  You can choose to listen for successful submissions and/or those that fail validation.  You should make every effort to integrate your application in this way instead of changing the XForms app itself.  We consider it an error in our own design if you are modifying the XForms source, so please let us know if that is the case.


Submitted Signal
----------------

This signal is sent when a new successful XForm comes in.  You are passed the XForm parameters in dict form as arguments.


Errored Signal
--------------

This signal is sent when a submission fails due to a validation error.   This means either a required field is missing or a field does not match the restrictions that were set for it.