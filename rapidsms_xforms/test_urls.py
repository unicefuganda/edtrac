from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from . import views
from . import urls
import rapidsms

# this file exists so as to add in the rapidsms-dashboard to our test set of URLs

urlpatterns = urls.urlpatterns

# examine all of the urlpatterns to see if there is a pattern
# defined for the root url / dashboard
has_dash = False
for pat in urlpatterns:
    if pat.regex.pattern == '^$':
        has_dash = True

# if there is no dashboard url, add the default
if not has_dash:
    from rapidsms.views import dashboard
    urlpatterns += patterns('', url(r'^$', dashboard, name='rapidsms-dashboard'),)

# add in rapidsms urls too
urlpatterns += url(r'^accounts/login/$', rapidsms.views.login, name='rapidsms-login'),
urlpatterns += url(r'^accounts/logout/$', rapidsms.views.logout, name='rapidsms-logout'),
