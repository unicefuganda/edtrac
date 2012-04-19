from django.contrib import admin

from .models import Role, UserProfile, School, EmisReporter

admin.site.register(Role)
admin.site.register(School)
admin.site.register(UserProfile)
admin.site.register(EmisReporter)