#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


from django.template import RequestContext
from django.shortcuts import render_to_response
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.contrib.auth.views import login as django_login
from django.contrib.auth.views import logout as django_logout
from django.conf import settings


@require_GET
def dashboard(req):
    return render_to_response(
        "dashboard.html",
        context_instance=RequestContext(req))

@never_cache
def login(req, template_name="rapidsms/login.html"):
    response = django_login(req, **{"template_name" : template_name})
    if getattr(settings, 'ENABLE_AUDITLOG', False):
        try:
            from auditlog.utils import audit_log
            if req.user.is_authenticated():
                log_dict = {'request': req, 'logtype': 'system', 'action':'login',
                            'detail':'User logged in %s:%s' % (req.user.id, req.user.username) }
                audit_log(log_dict)
        except ImportError:
            pass
    return response

@never_cache
def logout(req, template_name="rapidsms/loggedout.html"):
    if getattr(settings, 'ENABLE_AUDITLOG', False):
        try:
            from auditlog.utils import audit_log
            log_dict = {'request': req, 'logtype': 'system', 'action':'logout',
                        'detail':'User logged out %s:%s' % (req.user.id, req.user.username) }
            audit_log(log_dict)
        except ImportError:
            pass
    from django.contrib.auth import logout as user_logout
    user_logout(req)
    return render_to_response(template_name, locals(), context_instance=RequestContext(req))
