from .models import *

def copy_dashboard(from_dashboard, to_dashboard):
    for m in to_dashboard.modules.all():
        m.delete()
    for mod_obj in from_dashboard.modules.all():
        mod = to_dashboard.modules.create(title = mod_obj.title,
                                       view_name = mod_obj.view_name,
                                       column = mod_obj.column,
                                       offset = mod_obj.offset)
        mod.save()
        for param in mod_obj.params.all():
            mod_params = mod.params.create(param_name = param.param_name,
                                           param_value = param.param_value,
                                           is_url_param = param.is_url_param)
            mod_params.save()