from django.views.decorators.http import require_GET
from django.shortcuts import redirect, get_object_or_404
from django import forms

from rapidsms.utils import render_to_response
from .models import XForm, XFormSubmission, XFormField, XFormFieldConstraint

@require_GET
def xforms(req): 

    xforms = XForm.objects.all()
    breadcrumbs = (('XForms', ''),)
    return render_to_response(req, "xforms/form_index.html", { 'xforms': xforms, 'breadcrumbs': breadcrumbs } )


class NewXFormForm(forms.ModelForm): # pragma: no cover
    class Meta:
        model = XForm
        fields = ('name', 'keyword', 'description', 'response')

class EditXFormForm(forms.ModelForm): # pragma: no cover
    class Meta:
        model = XForm
        fields = ('name', 'keyword', 'description', 'response', 'active')

def new_xform(req):
    if req.method == 'POST':
        form = NewXFormForm(req.POST)
        if form.is_valid():
            # create our XForm
            xform = form.save(commit=False)

            # set the user
            xform.owner = req.user

            # commit it
            xform.save()

            return redirect("/xforms/%d/view/" % xform.pk)
    else:
        form = NewXFormForm()

    return render_to_response(req, "xforms/form_create.html", { 'form': form } )


def view_form(req, form_id):
    xform = XForm.objects.get(pk=form_id)
    fields = XFormField.objects.order_by('order').filter(xform=xform)
    breadcrumbs = (('XForms', '/xforms'),('Edit Form', ''))
    return render_to_response(req, "xforms/form_view.html", { 'xform': xform, 'fields': fields, 'field_count' : len(fields), 'breadcrumbs' : breadcrumbs })

def view_form_details(req, form_id):
    xform = XForm.objects.get(pk=form_id)
    return render_to_response(req, "xforms/form_details.html", { 'xform': xform })

def edit_form(req, form_id):
    xform = XForm.objects.get(pk=form_id)
    fields = XFormField.objects.order_by('order').filter(xform=xform)

    breadcrumbs = (('XForms', '/xforms'),('Edit Form', ''))

    if req.method == 'POST':
        form = EditXFormForm(req.POST, instance=xform)
        if form.is_valid():
            xform = form.save()
            return render_to_response(req, "xforms/form_details.html", {"xform" : xform})
    else:
        form = EditXFormForm(instance=xform)

    return render_to_response(req, "xforms/form_edit.html", { 'form': form, 'xform': xform, 'fields': fields, 'field_count' : len(fields), 'breadcrumbs' : breadcrumbs })


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
        fields = ('type', 'caption', 'command', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'cols': 80, 'rows': 20}),
        }

class ConstraintForm(forms.ModelForm):
    class Meta:
        model = XFormFieldConstraint
        fields = ('type', 'test', 'message') # Why do we need order?
        
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
            return render_to_response(req, "xforms/field_view.html", {'field' : field, 'xform' : xform })
    else:
        form = FieldForm()

    return render_to_response(req, "xforms/field_edit.html", { 'form': form, 'xform': xform })

def view_submissions(req, form_id):
    xform = XForm.objects.get(pk=form_id)

    submissions = xform.submissions.all().order_by('-pk')
    fields = xform.fields.all().order_by('pk')

    breadcrumbs = (('XForms', '/xforms'),('Submissions', ''))
    
    return render_to_response(req, "xforms/submissions.html", { 'xform': xform, 'fields': fields, 'submissions': submissions, 'breadcrumbs': breadcrumbs })

def make_submission_form(xform):
    fields = {}
    for field in xform.fields.all().order_by('order'):
        fields[field.command] = forms.CharField(required=False,
                                                help_text=field.description)

    # this method overloads Django's form clean() method and makes sure all the fields
    # pass the constraints determined by our XForm.  This guarantees that even the Admin
    # can't create forms that violate the constraints they set
    def clean(self):
        cleaned_data = self.cleaned_data

        for field in xform.fields.all():
            command = field.command
            if command in cleaned_data:
                field_val = str(cleaned_data.get(command))
                error_msg = field.check_value(field_val)

                # if there is an error, remove it from our cleaned data and 
                # add the error to our list of errors for this form
                if error_msg:
                    self._errors[field.command] = self.error_class([error_msg])
                    del cleaned_data[field.command]

        return cleaned_data

    # super neato Python magic to create a new class dynamically
    #  - first arg is the class name
    #  - second arg is the base class
    #  - third arg is the fields for the class
    return type('SubmissionForm', (forms.BaseForm,), { 'base_fields': fields, 'xform': xform, 'clean': clean })


def edit_submission(req, submission_id):
    submission = get_object_or_404(XFormSubmission, pk=submission_id)
    xform = submission.xform
    fields = xform.fields.all().order_by('order')
    values = submission.values.all()

    form_class = make_submission_form(xform)
    if req.method == 'POST':
        form = form_class(req.POST)

        # no errors?  save and redirect
        if form.is_valid():
            # update our submission
            xform.update_submission_from_dict(submission, form.cleaned_data)

            # redirect to the xform submission page
            return redirect("/xforms/%d/submissions" % xform.pk)
    else:
        # our hash of bound values
        form_vals = {}
        for value in values:
            form_vals[value.field.command] = value.value
        print form_vals

        form = form_class(form_vals)

    breadcrumbs = (('XForms', '/xforms'),('Submissions', '/xforms/%d/submissions' % xform.pk), ('Edit Submission', ''))

    return render_to_response(req, "xforms/submission_edit.html", { 'xform': xform, 'submission': submission,
                                                                    'fields': fields, 'values': values, 'form': form,
                                                                    'breadcrumbs': breadcrumbs })

def view_field(req, form_id, field_id):
    xform = XForm.objects.get(pk=form_id)
    field = XFormField.objects.get(pk=field_id)
    return render_to_response(req, "xforms/field_view.html", { 'xform': xform, 'field' : field })
    

def edit_field (req, form_id, field_id):
    xform = XForm.objects.get(pk=form_id)
    field = XFormField.objects.get(pk=field_id)
    constraints = XFormFieldConstraint.objects.filter(field=field) # Is order necessary for constraints?
    
    if req.method == 'POST':
        form = FieldForm(req.POST, instance=field)
        if form.is_valid():
            field = form.save(commit=False)
            field.xform = xform
            field.save()
            return render_to_response(req, "xforms/field_view.html", { 'form' : form, 'xform' : xform, 'field' : field })
        else:            return render_to_response(req, "xforms/field_edit.html", { 'form' : form, 'xform': xform, 'field' : field })
    else:
        form = FieldForm(instance=field)

    return render_to_response(req, "xforms/field_edit.html", { 'form' : form, 'xform': xform, 'field' : field })

def add_constraint(req, form_id, field_id):
    xform = XForm.objects.get(pk=form_id)
    field = XFormField.objects.get(pk=field_id)

    if req.method == 'POST':
        form = ConstraintForm(req.POST)
        if form.is_valid():
            constraint = form.save(commit=False)
            constraint.field = field
            constraint.save()
            print "saved %s %s" % (constraint.id, constraint.field.id)
        else:
            print "form invalid"
    else:
        form = ConstraintForm()
        
    return render_to_response(req, "xforms/onstraint_constraint.html", { 'form' : form, 'xform' : xform, 'field' : field });

def edit_constraint(req, form_id, field_id, constraint_id) :

    return render_to_response(req, "xforms/constraint_edit.html");


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
