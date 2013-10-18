# education/admin.py
from django.contrib import admin

from .models import Role, UserProfile, School, EmisReporter


class EmisReporterAdmin(admin.ModelAdmin):
    list_display = ('name', 'gender', 'active')
    search_fields = ['name']
    filter_horizontal = ['schools']


class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'no_of_reporters', 'location')
    list_filter = ('location',)
    search_fields = ['name']


admin.site.register(Role)
admin.site.register(School, SchoolAdmin)
admin.site.register(UserProfile)
admin.site.register(EmisReporter, EmisReporterAdmin)
