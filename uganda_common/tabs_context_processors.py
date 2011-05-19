"""A set of request processors that return dictionaries to be merged into a
template context. Each function takes the request object as its only parameter
and returns a dictionary to add to the context.
"""
from django.conf import settings
from django.core.urlresolvers import reverse
from ureport.settings import AUTHENTICATED_TABS

class Tab(object):
    def __init__(self, view, caption=None):
        self._caption = caption
        self._view = view

    def _auto_caption(self):
        func_name = self._view.split('.')[-1]       # my_view
        return func_name.replace("_", " ").title()  # My View

    @property
    def url(self):
        """
        Return the URL of this tab.

        Warning: If this tab's view function cannot be reversed, Django
        will silently ignore the exception, and return the value of the
        TEMPLATE_STRING_IF_INVALID setting.
        """
        return reverse(self._view)

    @property
    def caption(self):
        return self._caption or self._auto_caption()

def layout(request):
    """
    a context processor that changes adds Tabs to layout.html in RapidSMS. Tab loading is reworked to allow for privileged 
    user Tab access.                            
    """
    tabs = []
    for view, caption in settings.RAPIDSMS_TABS:
        tabs.append(Tab(view, caption))
       
    if not request.user.is_anonymous() and request.user:
       for view, caption in AUTHENTICATED_TABS:
           tabs.append(Tab(view, caption))
           
    return {
        "tabs":tabs
    }

