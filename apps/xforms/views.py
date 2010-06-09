from django.views.decorators.http import require_GET
from django.templatetags.tabs_tags import register_tab
from django.shortcuts import redirect
from django import forms
from rapidsms.utils import render_to_response
from .models import XForm, XFormField

@require_GET
@register_tab(caption="XForms")
def xforms(req):
    xforms = XForm.objects.all()
    return render_to_response(req, "xforms/xforms.html", { 'xforms': xforms } )


class XFormForm(forms.ModelForm):
    class Meta:
        model = XForm
        fields = ('name', 'slug', 'description')

def new_xform(req):
    if req.method == 'POST':
        form = XFormForm(req.POST)
        if form.is_valid():
            # create our XForm
            xform = form.save(commit=False)

            # set the user
            xform.owner = req.user

            # commit it
            xform.save()

            return redirect("/xforms/%d/add_field/" % xform.pk)
    else:
        form = XFormForm()

    return render_to_response(req, "xforms/new.html", { 'form': form } )


def edit_xform(req, form_id):
    xform = XForm.objects.get(pk=form_id)
    fields = XFormField.objects.filter(xform=xform)

    if req.method == 'POST':
        form = XFormForm(req.POST, instance=xform)
        if form.is_valid():
            xform = form.save()
            return render_to_response(req, "xforms/edit.html", { 'form': form, 'xform': xform, 'fields': fields } )
    else:
        form = XFormForm(instance=xform)

    return render_to_response(req, "xforms/edit.html", { 'form': form, 'xform': xform, 'fields': fields } )
    

class FieldForm(forms.ModelForm):
    class Meta:
        model = XFormField
        fields = ('type', 'name', 'description', 'required')

def add_field(req, form_id):
    xform = XForm.objects.get(pk=form_id)

    if req.method == 'POST':
        form = FieldForm(req.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.xform = xform
            field.save()
            return redirect("/xforms/%d/edit/" % xform.pk)
    else:
        form = FieldForm()

    return render_to_response(req, "xforms/add_field.html", { 'form': form, 'xform': xform })

