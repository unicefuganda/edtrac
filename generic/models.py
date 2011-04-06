from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

class Dashboard(models.Model):
    """
    Dashboards are the landing (default) pages for the different application built into
    rapidsms. Each user of the application can define what appears on their landing page
    and the arrangement of the different modules and their individual behavior / configuration
    is customizable by the user.
    """
    user            = models.ForeignKey(User)
    slug            = models.CharField(max_length=50, unique=True)
    
    def __unicode__(self):
        return "%s"%self.user

class Module(models.Model):
    """
    Modules are the different applications that run / display on a user dashboard. Modules are
    customizable by the user in terms of where they display on the dashboard and how they behave.
    """
    dashboard       = models.ForeignKey(Dashboard, related_name = "modules")
    title           = models.CharField(max_length=30)
    view_name       = models.CharField(max_length=30)
    offset          = models.IntegerField()
    column          = models.IntegerField()
    
    def get_absolute_url(self):
        url = reverse(self.view_name, kwargs=self._param_dict())
        params = self._param_http()
        if params:
            url = "%s?%s" % (url, params)
        return url

    def _param_dict(self):
        return dict([(m.param_name, m.param_value,) for m in self.params.filter(is_url_param=True)])

    def _param_http(self):
        return '&'.join(['%s=%s' % (m.param_name, m.param_value) for m in self.params.filter(is_url_param=False)])
    
    def __unicode__(self):
        return "%s"%self.view_name

class ModuleParams(models.Model):
    """
    Module Parameters specify the different configurations and configuration values for each module
    on the dashboard. These parameters or configurations can be changed by the owner of the dashboard.
    """
    module          = models.ForeignKey(Module, related_name = 'params')
    param_name      = models.CharField(max_length=30)
    param_value     = models.CharField(max_length=30)
    is_url_param    = models.BooleanField()
    
    def __unicode__(self):
        return "%s"%self.param_name