from django.contrib import admin
from generic.models import *

class dashboardAdmin(admin.ModelAdmin):
    """dashboard admin """
class moduleAdmin(admin.ModelAdmin):
    """module admin """
class moduleParamsAdmin(admin.ModelAdmin):
    """module params admin """


admin.site.register(Dashboard,dashboardAdmin)
admin.site.register(Module,moduleAdmin)
admin.site.register(ModuleParams,moduleParamsAdmin)