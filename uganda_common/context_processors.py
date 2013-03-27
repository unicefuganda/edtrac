"""A set of request processors that return dictionaries to be merged into a
template context. Each function takes the request object as its only parameter
and returns a dictionary to add to the context.
"""
from django.conf import settings
from django.db.utils import DatabaseError
from rapidsms.templatetags.tabs_tags import Tab
from uganda_common.models import Access


def authtabs(request):
    """
    a context processor that adds Tabs to layout.html in RapidSMS. Tab loading is reworked to allow for privileged 
    user Tab access.                            
    """
    tabs = []
    for view, caption in settings.RAPIDSMS_TABS:
        tabs.append(Tab(view, caption))
    try:
        if request.user.is_authenticated():
            auth_tabs = getattr(settings, 'AUTHENTICATED_TABS', [])
            for view, caption in auth_tabs:
                tabs.append(Tab(view, caption))
            try:
                access = Access.objects.get(user=request.user)
                for i in range(len(tabs)):
                    if access.denied(request, u_path=tabs[i].url):
                        tabs.remove(tabs[i])
            except Access.DoesNotExist:
                pass
            except DatabaseError:
                pass
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

