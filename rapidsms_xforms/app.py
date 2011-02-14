import rapidsms

from rapidsms.apps.base import AppBase
from .models import XForm

class App (AppBase):

    def handle (self, message):
        # see if this message matches any of our forms
        form = XForm.find_form(message.text)

        # if so, process it
        if form:
            submission = form.process_sms_submission(message)
            message.respond(submission.response)
            return True

        return False
        
