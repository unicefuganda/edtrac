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

            return redirect("/xforms/%d/edit/" % xform.pk)
    else:
        form = XFormForm()

    return render_to_response(req, "xforms/new.html", { 'form': form } )


def edit_xform(req, form_id):
    xform = XForm.objects.get(pk=form_id)
    fields = XFormField.objects.order_by('order').filter(xform=xform)

    if req.method == 'POST':
        form = XFormForm(req.POST, instance=xform)
        if form.is_valid():
            xform = form.save()
            return redirect("/xforms")
    else:
        form = XFormForm(instance=xform)

    return render_to_response(req, "xforms/edit.html", { 'form': form, 'xform': xform, 'fields': fields } )

def order_xform (req, form_id):
	if req.method == 'POST':
		
		field_ids = req.POST['order'].split(',')
		count = 1
		for field_id in field_ids:
			field = XFormField.objects.get(pk=field_id)
			field.order = count
			count = count + 1
			field.save()
			
		return render_to_response(req, "xforms/ajax_complete.html", {'ids' : field_ids})

class FieldForm(forms.ModelForm):
    class Meta:
        model = XFormField
        fields = ('type', 'name', 'description', 'required')
        description = forms.CharField(widget=forms.Textarea)

def add_field(req, form_id):
    xform = XForm.objects.get(pk=form_id)
    fields = XFormField.objects.filter(xform=xform)

    if req.method == 'POST':
        form = FieldForm(req.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.xform = xform
            field.order = len(fields)
            field.save()
            return redirect("/xforms/%d/edit/" % xform.pk)
    else:
        form = FieldForm()

    return render_to_response(req, "xforms/add_field.html", { 'form': form, 'xform': xform })

def edit_field (req, form_id, field_id):
	xform = XForm.objects.get(pk=form_id)
	field = XFormField.objects.get(pk=field_id)
	
	if req.method == 'POST':
		form = FieldForm(req.POST, instance=field)
		if form.is_valid():
			field = form.save(commit=False)
			field.xform = xform
			field.save()
			return redirect("/xforms/%d/edit/" % xform.pk)
		else:
			fields = XFormField.objects.filter(xform=xform)
			return render_to_response(req, "xforms/edit.html", { 'form' : form, 'xform': xform, 'field' : field, 'fields':fields })
	else:
		form = FieldForm(instance=field)

	return render_to_response(req, "xforms/edit_field.html", { 'form' : form, 'xform': xform, 'field' : field })

def delete_xform (req, form_id):
	xform = XForm.objects.get(pk=form_id)
	if req.method == 'POST':
		xform.delete()
		
	return redirect("/xforms")

def delete_field (req, form_id, field_id):
	xform = XForm.objects.get(pk=form_id)
	field = XFormField.objects.get(pk=field_id)

	if req.method == 'POST':
		field.delete()
		
	return redirect("/xforms/%d/edit/" % xform.pk)
