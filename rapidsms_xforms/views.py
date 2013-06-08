from django.views.decorators.http import require_GET, require_POST
from django.template import RequestContext
from django.shortcuts import redirect, get_object_or_404, render_to_response
from django.conf import settings
from django import forms
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sites.models import Site

from .models import XForm, XFormSubmission, XFormField, XFormFieldConstraint
from xml.dom.minidom import parse, parseString
from eav.fields import EavSlugField

from uni_form.helpers import FormHelper, Layout, Fieldset
from django.core.paginator import Paginator
from django_digest import HttpDigestAuthenticator
from django.http import HttpResponse

# CSV Export
@require_GET
def submissions_as_csv(req, pk):
    xform = get_object_or_404(XForm, pk=pk)

    submissions = xform.submissions.all().order_by('-pk')
    fields = xform.fields.all().order_by('pk')

    resp = render_to_response(
        "xforms/submissions.csv",
        {'xform': xform, 'submissions': submissions, 'fields': fields},
        mimetype="text/csv",
        context_instance=RequestContext(req))
    resp['Content-Disposition'] = 'attachment;filename="%s.csv"' % xform.keyword
    return resp

# ODK Endpoints
@require_GET
def odk_list_forms(req):
    # if forms are restricted, force digest authentication
    if getattr(settings, 'AUTHENTICATE_XFORMS', False):
        authenticator = HttpDigestAuthenticator()
        if not authenticator.authenticate(req):
            return authenticator.build_challenge_response()

    xforms = []
    for form in XForm.on_site.filter(active=True):
        if form.does_user_have_permission(req.user):
            xforms.append(form)

    return render_to_response(
        "xforms/odk_list_forms.xml",
        { 'xforms': xforms, 'host':  settings.XFORMS_HOST },
        mimetype="text/xml",
        context_instance=RequestContext(req))

@require_GET
def odk_get_form(req, pk):
    # if forms are restricted, force digest authentication
    if getattr(settings, 'AUTHENTICATE_XFORMS', False):
        authenticator = HttpDigestAuthenticator()
        if not authenticator.authenticate(req):
            return authenticator.build_challenge_response()

    xform = get_object_or_404(XForm, pk=pk)
    if not xform.does_user_have_permission(req.user):
        return HttpResponse("You do not have permission to view this form", status=403)

    resp = render_to_response(
        "xforms/odk_get_form.xml", { 'xform': xform },
        mimetype="text/xml",
        context_instance=RequestContext(req))
    resp['Content-Disposition'] = 'attachment;filename="%s.xml"' % xform.keyword
    return resp

@csrf_exempt
def odk_submission(req):
    # if forms are restricted, force digest authentication
    if getattr(settings, 'AUTHENTICATE_XFORMS', False):
        authenticator = HttpDigestAuthenticator()
        if not authenticator.authenticate(req):
            return authenticator.build_challenge_response()

    if req.method == 'HEAD':
        # technically this should be a 201 according to the HTTP spec, but
        # ODK collect requires 204 to move forward
        return HttpResponse("OK", status=204)
    elif req.method != 'POST':
        # only POST and HEAD are supported
        return HttpResponse("Invalid method", status=405)

    values = {}
    xform = None
    raw = ""

    # this is the raw data
    if 'xml_submission_file' in req.FILES:
        file = req.FILES['xml_submission_file']
        raw = file.file.read()
        dom = parseString(raw)
        root = dom.childNodes[0]
        for child in root.childNodes:
            tag = child.tagName
            if child.childNodes:
                body = child.childNodes[0].wholeText

                if tag == 'xform-keyword':
                    xform = get_object_or_404(XForm, keyword=body)
                else:
                    values[tag] = body

    # every other file is a binary, save them in our map as well (the keys are the values
    # in the submission file above)
    binaries = dict()
    for key in req.FILES:
        if key != 'xml_submission_file':
            binaries[key] = req.FILES[key].file.read()

    # check that they have the correct permissions
    if not xform.does_user_have_permission(req.user):
        return HttpResponse("You do not have permission to view this form", status=403)

    # if we found the xform
    submission = xform.process_odk_submission(raw, values, binaries)

    resp = render_to_response(
        "xforms/odk_submission.xml",
        { "xform": xform, "submission": submission },
        context_instance=RequestContext(req))

    # ODK needs two things for a form to be considered successful
    # 1) the status code needs to be 201 (created)
    resp.status_code = 201

    # 2) The location header needs to be set to the host it posted to
    resp['Location'] = "http://%s/submission" % settings.XFORMS_HOST
    return resp


@require_GET
def xforms(req):
    xforms = XForm.on_site.all()
    breadcrumbs = (('XForms', ''),)
    return render_to_response(
        "xforms/form_index.html",
        { 'xforms': xforms, 'breadcrumbs': breadcrumbs },
        context_instance=RequestContext(req))

def XFormForm(*args, **kwargs):
    required_fields = ['Form Settings', 'name', 'keyword', 'description', 'response', 'active']
    form_fields = ['name', 'keyword', 'keyword_prefix', 'command_prefix', 'separator', 'description', 'response', 'active', 'restrict_to', 'restrict_message']

    if 'excludes' in kwargs:
        excludes = kwargs.pop('excludes')
        for exclude in excludes:
            required_fields.remove(exclude)
            form_fields.remove(exclude)

    class CustomXFormForm(forms.ModelForm):

        def clean(self):
            cleaned = super(CustomXFormForm, self).clean()

            # if they are restricting to a group
            if cleaned['restrict_to'] and not cleaned['restrict_message']:
                raise forms.ValidationError("You must enter a message to display if you are restricting the form.")

            return cleaned

        class Meta:
            model = XForm
            fields = form_fields

        helper = FormHelper()
        layout = Layout(
            # required fields
            Fieldset(*required_fields),

            # optional attributes
            Fieldset('Advanced Settings',
                     'keyword_prefix',
                     'command_prefix',
                     'separator',
                     ),

            # security
            Fieldset('Security',
                     'restrict_to',
                     'restrict_message',
                     )
            )

        helper.add_layout(layout)

    return CustomXFormForm(*args, **kwargs)

def new_xform(req):
    if req.method == 'POST':
        form = XFormForm(req.POST, excludes=('active',))
        if form.is_valid():
            # create our XForm
            xform = form.save(commit=False)

            # set the user
            xform.owner = req.user

            # and the site
            xform.site = Site.objects.get_current()

            # add the separators
            xform.separator = form.cleaned_data['separator']
            # commit it
            xform.save()

            return redirect("/xforms/%d/view/" % xform.pk)
    else:
        form = XFormForm(excludes=('active',))

    breadcrumbs = (('XForms', '/xforms/'), ('New XForm', ''))

    return render_to_response(
        "xforms/form_create.html", { 'form': form, 'breadcrumbs': breadcrumbs },
        context_instance=RequestContext(req))


def view_form(req, form_id):
    xform = XForm.on_site.get(pk=form_id)
    fields = XFormField.objects.order_by('order').filter(xform=xform)
    breadcrumbs = (('XForms', '/xforms/'), ('Edit Form', ''))
    return render_to_response("xforms/form_view.html",
        { 'xform': xform, 'fields': fields, 'field_count' : len(fields), 'breadcrumbs' : breadcrumbs },
        context_instance=RequestContext(req))

def view_form_details(req, form_id):
    xform = XForm.on_site.get(pk=form_id)
    return render_to_response("xforms/form_details.html",
        { 'xform': xform },
        context_instance=RequestContext(req))

def edit_form(req, form_id):
    xform = XForm.on_site.get(pk=form_id)

    fields = XFormField.objects.order_by('order').filter(xform=xform)

    breadcrumbs = (('XForms', '/xforms/'), ('Edit Form', ''))

    if req.method == 'POST':
        form = XFormForm(req.POST, instance=xform)
        if form.is_valid():
            xform = form.save()
            xform.separator = form.cleaned_data['separator']
            xform.save()
            return render_to_response("xforms/form_details.html",
                {"xform" : xform},
                context_instance=RequestContext(req))
    else:
        form = XFormForm(instance=xform)

    return render_to_response("xforms/form_edit.html",
        { 'form': form, 'xform': xform, 'fields': fields, 'field_count' : len(fields), 'breadcrumbs' : breadcrumbs },
        context_instance=RequestContext(req))


def order_xform (req, form_id):
    if req.method == 'POST':
        field_ids = req.POST['order'].split(',')
        count = 1
        for field_id in field_ids:
            field = XFormField.objects.get(pk=field_id)
            field.order = count
            count = count + 1
            field.save()

        return render_to_response("xforms/ajax_complete.html",
            {'ids' : field_ids},
            context_instance=RequestContext(req))

class FieldForm(forms.ModelForm):

    def updateTypes(self):
        self.fields['field_type'].widget.choices = [(choice['type'], choice['label']) for choice in XFormField.TYPE_CHOICES.values()]

    def clean_field_type(self):
        toret = self.cleaned_data['field_type']
        if self.xform.separator.find('.') >= 0 and XFormField.TYPE_CHOICES[toret]['db_type'] == XFormField.TYPE_FLOAT:
            raise forms.ValidationError("You cannot have float values along with period (.) separators in an XForm.  Please edit the XForm separators and try again.")
        return toret

    class Meta:
        model = XFormField
        fields = ('field_type', 'name', 'command', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'cols': 30, 'rows': 2}),
            'field_type': forms.Select(),
        }

class ConstraintForm(forms.ModelForm):
    class Meta:
        model = XFormFieldConstraint
        fields = ('type', 'test', 'message')  # Why do we need order?

@csrf_exempt
def add_field(req, form_id):
    xform = XForm.on_site.get(pk=form_id)
    fields = XFormField.objects.filter(xform=xform)

    if req.method == 'POST':
        form = FieldForm(req.POST)
        form.updateTypes()
        form.xform = xform
        if form.is_valid():
            field = form.save(commit=False)
            field.xform = xform
            field.order = len(fields)
            field.save()
            return render_to_response("xforms/field_view.html",
                {'field' : field, 'xform' : xform },
                context_instance=RequestContext(req))
    else:
        form = FieldForm()
        form.updateTypes()

    return render_to_response("xforms/field_edit.html",
        { 'form': form, 'xform': xform },
        context_instance=RequestContext(req))

def view_submissions(req, form_id):
    xform = XForm.on_site.get(pk=form_id)

    submissions = xform.submissions.all().order_by('-pk')
    fields = xform.fields.all().order_by('pk')

    breadcrumbs = (('XForms', '/xforms/'), ('Submissions', ''))

    current_page = 1
    if 'page' in req.REQUEST:
        current_page = int(req.REQUEST['page'])

    paginator = Paginator(submissions, 25)
    page = paginator.page(current_page)

    return render_to_response("xforms/submissions.html",
                              dict(xform=xform, fields=fields, submissions=page, breadcrumbs=breadcrumbs,
                                   paginator=paginator, page=page),
                              context_instance=RequestContext(req))

def make_submission_form(xform):
    fields = {}
    for field in xform.fields.all().order_by('order'):
        if field.xform_type() == 'binary':
            fields[field.command] = forms.FileField(required=False,
                                                    help_text=field.description,
                                                    label=field.name)
        else:
            fields[field.command] = forms.CharField(required=False,
                                                    help_text=field.description,
                                                    label=field.name)

    # this method overloads Django's form clean() method and makes sure all the fields
    # pass the constraints determined by our XForm.  This guarantees that even the Admin
    # can't create forms that violate the constraints they set
    def clean(self):
        cleaned_data = self.cleaned_data

        for field in xform.fields.all():
            command = field.command
            if command in cleaned_data:
                field_val = cleaned_data.get(command)

                if field.xform_type() == 'binary':
                    if field_val is None:
                        cleaned_data[command] = None
                    elif field_val == False:
                        del cleaned_data[field.command]
                    else:
                        typedef = XFormField.lookup_type(field.field_type)
                        cleaned_val = typedef['parser'](field.command, field_val.read(), filename=field_val.name)
                        cleaned_data[command] = cleaned_val
                else:
                    try:
                        cleaned_val = field.clean_submission(field_val, 'sms')
                        cleaned_data[command] = cleaned_val
                    except ValidationError as err:
                        # if there is an error, remove it from our cleaned data and
                        # add the error to our list of errors for this form
                        self._errors[field.command] = self.error_class(err.messages)
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
        form = form_class(req.POST, req.FILES)

        # no errors?  save and redirect
        if form.is_valid():

            # update our submission
            xform.update_submission_from_dict(submission, form.cleaned_data)
            if getattr(settings, 'ENABLE_AUDITLOG', False):
                from auditlog.utils import audit_log
                log_dict = {'request': req, 'logtype': 'xform', 'action':'edit',
                            'detail':'Edited report (submission) id:%s' % submission_id }
                audit_log(log_dict)
            # redirect to the xform submission page
            return redirect("/xforms/%d/submissions/" % xform.pk)
    else:
        # our hash of bound values
        form_vals = {}
        file_data = {}
        for value in values:
            field = XFormField.objects.get(pk=value.attribute.pk)
            if field.xform_type() == 'binary' and value.value:
                form_vals[field.command] = value.value.binary
            else:
                form_vals[field.command] = value.value

        form = form_class(initial=form_vals)

    breadcrumbs = (('XForms', '/xforms/'), ('Submissions', '/xforms/%d/submissions/' % xform.pk), ('Edit Submission', ''))
    back_url = getattr(settings, 'XFORM_CANCEL_BACKURL', '/hc/reports/')
    return render_to_response("xforms/submission_edit.html",
        { 'xform': xform, 'submission': submission,
        'fields': fields, 'values': values, 'form': form,
        'breadcrumbs': breadcrumbs, 'back_url':back_url },
        context_instance=RequestContext(req))

def view_field(req, form_id, field_id):
    xform = XForm.on_site.get(pk=form_id)
    field = XFormField.objects.get(pk=field_id)
    return render_to_response("xforms/field_view.html",
        { 'xform': xform, 'field' : field },
        context_instance=RequestContext(req))

@csrf_exempt
def edit_field (req, form_id, field_id):
    xform = XForm.on_site.get(pk=form_id)
    field = XFormField.objects.get(pk=field_id)
    if req.method == 'POST':
        form = FieldForm(req.POST, instance=field)
        form.updateTypes()
        form.xform = xform
        if form.is_valid():
            field = form.save(commit=False)
            field.xform = xform
            field.save()
            return render_to_response("xforms/field_view.html",
                { 'form' : form, 'xform' : xform, 'field' : field },
                context_instance=RequestContext(req))
        else:            return render_to_response("xforms/field_edit.html",
                            { 'form' : form, 'xform': xform, 'field' : field },
                            context_instance=RequestContext(req))
    else:
        form = FieldForm(instance=field)
        form.updateTypes()

    return render_to_response("xforms/field_edit.html",
        { 'form' : form, 'xform': xform, 'field' : field },
        context_instance=RequestContext(req))


def delete_xform (req, form_id):
    xform = XForm.on_site.get(pk=form_id)
    if req.method == 'POST':
        xform.delete()

    return redirect("/xforms/")

def delete_field (req, form_id, field_id):
    xform = XForm.on_site.get(pk=form_id)
    field = XFormField.objects.get(pk=field_id)

    if req.method == 'POST':
        field.delete()

    return redirect("/xforms/%d/edit/" % xform.pk)

@csrf_exempt
def add_constraint(req, form_id, field_id):
    xform = XForm.on_site.get(pk=form_id)
    field = XFormField.objects.get(pk=field_id)
    constraints = XFormFieldConstraint.objects.order_by('order').filter(field=field)
    form = ConstraintForm()

    if req.method == 'POST':
        form = ConstraintForm(req.POST)
        if form.is_valid():
            constraint = form.save(commit=False)
            constraint.field = field
            constraint.order = len(constraints)
            constraint.save()
            return render_to_response("xforms/table_row_view.html",
                {'item' : constraint, 'columns': constraint_columns, 'buttons' : constraint_buttons, 'field' : field, 'xform' : xform },
                context_instance=RequestContext(req))
    else:
        form = ConstraintForm()

    return render_to_response("xforms/table_row_edit.html",
        { 'buttons' : add_button, 'form' : form, 'xform' : xform, 'field' : field },
        context_instance=RequestContext(req))

@csrf_exempt
def edit_constraint(req, form_id, field_id, constraint_id) :

    xform = XForm.on_site.get(pk=form_id)
    field = XFormField.objects.get(pk=field_id)
    constraint = XFormFieldConstraint.objects.get(pk=constraint_id)

    if req.method == 'POST':
        form = ConstraintForm(req.POST, instance=constraint)
        if form.is_valid():
            constraint = form.save(commit=False)
            constraint.field = field
            constraint.save()
            return render_to_response("xforms/table_row_view.html",
                {  'columns' : constraint_columns, 'buttons' : constraint_buttons, 'item' : constraint, 'form' : form, 'xform' : xform, 'field' : field },
                context_instance=RequestContext(req))
        else:
            return render_to_response("xforms/table_row_edit.html",
                { 'buttons' : save_button, 'item' : constraint, 'form' : form, 'xform' : xform, 'field' : field },
                context_instance=RequestContext(req))
    else:
        form = ConstraintForm(instance=constraint)

    return render_to_response("xforms/table_row_edit.html",
        { 'buttons' : save_button, 'form' : form, 'xform': xform, 'field' : field, 'item' : constraint },
        context_instance=RequestContext(req))

def view_constraint(req, form_id, field_id, constraint_id) :

    xform = XForm.on_site.get(pk=form_id)
    field = XFormField.objects.get(pk=field_id)
    constraint = XFormFieldConstraint.objects.get(pk=constraint_id)
    return render_to_response("xforms/table_row_view.html",
        { 'columns' : constraint_columns, 'buttons' : constraint_buttons, 'item' : constraint, 'xform' : xform, 'field' : field },
        context_instance=RequestContext(req))


def view_constraints(req, form_id, field_id):
    xform = XForm.on_site.get(pk=form_id)
    field = XFormField.objects.get(pk=field_id)
    constraints = XFormFieldConstraint.objects.order_by('order').filter(field=field)

    breadcrumbs = (('XForms', '/xforms/'), (xform.name, "/xforms/%s/view/" % xform.pk), ("Constraints", ''))

    return render_to_response("xforms/constraints.html",
        {  'xform' : xform, 'field' : field, 'table' : constraints, 'buttons' : constraint_buttons, 'columns' : constraint_columns, 'breadcrumbs': breadcrumbs },
        context_instance=RequestContext(req))

def delete_constraint (req, form_id, field_id, constraint_id):
    constraint = XFormFieldConstraint.objects.get(pk=constraint_id)
    if req.method == 'POST':
        constraint.delete()

    return redirect("/xforms/%s/field/%s/constraints/" % (form_id, field_id))

def order_constraints (req, form_id, field_id):
    if req.method == 'POST':
        constraint_ids = req.POST['order'].split(',')
        count = 1
        for constraint_id in constraint_ids:
            constraint = XFormFieldConstraint.objects.get(pk=constraint_id)
            constraint.order = count
            count = count + 1
            constraint.save()

        return render_to_response("xforms/ajax_complete.html",
            {'ids' : constraint_ids},
            context_instance=RequestContext(req))


add_button = ({ "image" : "rapidsms/icons/silk/decline.png", 'click' : 'cancelAdd'},
              { "text" : "Add", "image" : "rapidsms/icons/silk/add.png", 'click' : 'add'},)

save_button = ({ "image" : "rapidsms/icons/silk/decline.png", 'click' : 'cancelSave'},
                { "text" : "Save", "image" : "rapidsms_xforms/icons/silk/bullet_disk.png", 'click' : 'saveRow'},)
constraint_buttons = ({"image" : "rapidsms/icons/silk/delete.png", 'click' : 'deleteRow'},
                      { "text" : "Edit", "image" : "rapidsms_xforms/icons/silk/pencil.png", 'click' : 'editRow'},)
constraint_columns = (('Type', 'type'), ('Test', 'test'), ('Message', 'message'))


