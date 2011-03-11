from django.contrib import admin
from script.models import ScriptProgress,ScriptStep,Script

class ScriptStepAdmin(admin.ModelAdmin):
    """script progress admin """
class ScriptProgressAdmin(admin.ModelAdmin):
    """script progress admin """
class ScriptAdmin(admin.ModelAdmin):
    """script admin """


admin.site.register(ScriptProgress,ScriptProgressAdmin)
admin.site.register(Script,ScriptAdmin)
admin.site.register(ScriptStep,ScriptStepAdmin)