from django.contrib import admin
from .models import XForm, XFormField, XFormSubmission, XFormSubmissionValue

admin.site.register(XForm)
admin.site.register(XFormField)
admin.site.register(XFormSubmission)
admin.site.register(XFormSubmissionValue)

