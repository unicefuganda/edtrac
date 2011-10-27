"""A set of request processors that return dictionaries to be merged into a
template context. Each function takes the request object as its only parameter
and returns a dictionary to add to the context.
"""
from django.conf import settings
from django.core.urlresolvers import reverse
from rapidsms.templatetags.tabs_tags import Tab

def authtabs(request):
    """
    a context processor that adds Tabs to layout.html in RapidSMS. Tab loading is reworked to allow for privileged 
    user Tab access.                            
    """
    tabs = []
    for view, caption in settings.RAPIDSMS_TABS:
        tabs.append(Tab(view, caption))
    try:
        if not request.user.is_anonymous() and request.user:
            auth_tabs = getattr(settings, 'AUTHENTICATED_TABS', [])
            for view, caption in auth_tabs:
                tabs.append(Tab(view, caption))
        for tab in tabs:
            tab.is_active = tab.url == request.get_full_path()

        return {
            "tabs":tabs
        }
    except:
        return {}


def module(request):
    if request.GET and 'as_module' in request.GET:
        return {
            "as_module":True
        }
    return {}

