#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


from django.template import RequestContext
from django.shortcuts import render_to_response
from django.views.decorators.http import require_GET
from django.contrib.auth.views import login as django_login
from django.contrib.auth.views import logout as django_logout
from auditlog.utils import audit_log


@require_GET
def dashboard(req):
    return render_to_response(
        "dashboard.html",
        context_instance=RequestContext(req))


def login(req, template_name="rapidsms/login.html"):
    response = django_login(req, **{"template_name" : template_name})
    if req.user.is_authenticated():
        log_dict = {'request': req, 'logtype': 'system', 'action':'login',
                    'detail':'User logged in %s:%s' % (req.user.id, req.user.username) }
        audit_log(log_dict)
    return response


def logout(req, template_name="rapidsms/loggedout.html"):
    log_dict = {'request': req, 'logtype': 'system', 'action':'logout',
                    'detail':'User logged out %s:%s' % (req.user.id, req.user.username) }
    audit_log(log_dict)
    return django_logout(req, **{"template_name" : template_name})
