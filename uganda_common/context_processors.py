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
    print request.get_full_path()
    tabs = []
    for view, caption in settings.RAPIDSMS_TABS:
        tabs.append(Tab(view, caption))
       
    if not request.user.is_anonymous() and request.user:
        auth_tabs = getattr(settings, 'AUTHENTICATED_TABS',[])
        for view, caption in auth_tabs:
            tabs.append(Tab(view, caption))
    for tab in tabs:
        tab.is_active = tab.url == request.get_full_path()
    
    return {
        "tabs":tabs
    }

def layout(request):
    """
    a context processor that changes the base css of the layout.html in RapidSMS. This is useful in case you want to
    have a custom skin for RapidSMS.
    """
    css = settings.BASE_CSS if settings.BASE_CSS else "/static/rapidsms/stylesheets/layout.css"
    return {
        "BASE_CSS":settings.BASE_CSS
    }

