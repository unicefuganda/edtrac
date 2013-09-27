from django.contrib import admin

from .models import Role, UserProfile, School, EmisReporter


class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'location']


admin.site.register(Role)
admin.site.register(School, SchoolAdmin)
admin.site.register(UserProfile)
admin.site.register(EmisReporter)
