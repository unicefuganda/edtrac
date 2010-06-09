from django.contrib import admin
from .models import XForm
from .models import XFormField

admin.site.register(XForm)
admin.site.register(XFormField)

