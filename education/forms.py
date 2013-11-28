from django import forms
from django.forms import extras
import datetime
from mptt.forms import TreeNodeChoiceField
from education.utils import is_empty
from poll.models import Poll
from rapidsms.contrib.locations.models import Location
from generic.forms import ActionForm, FilterForm, ModuleForm
from mptt.forms import TreeNodeChoiceField
from rapidsms.contrib.locations.models import Location
from rapidsms.models import Backend
from .reports import get_week_date, get_month_day_range
from .models import School, EmisReporter, ReportComment
from rapidsms_xforms.models import XFormSubmissionValue
from django.contrib.auth.models import Group, User
from django.db.models import Q
from uganda_common.forms import SMSInput
from django.conf import settings
from rapidsms_httprouter.models import Message
from django.contrib.sites.models import Site
from contact.models import MassText
from rapidsms.models import Connection, Contact
from script.models import Script
from unregister.models import Blacklist

date_range_choices = (('w', 'Previous Calendar Week'), ('m', 'Previous Calendar Month'), ('q', 'Previous calendar quarter'),)

class DateRangeForm(forms.Form): # pragma: no cover
    start = forms.IntegerField(required=True, widget=forms.HiddenInput())
    end = forms.IntegerField(required=True, widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = self.cleaned_data

        start_ts = cleaned_data.get('start')
        cleaned_data['start'] = datetime.datetime.fromtimestamp(float(start_ts))

        end_ts = cleaned_data.get('end')
        cleaned_data['end'] = datetime.datetime.fromtimestamp(float(end_ts))
        return cleaned_data

AREAS = Location.tree.all().select_related('type')


class ReporterFreeSearchForm(FilterForm):

    """ concrete implementation of filter form
        TO DO: add ability to search for multiple search terms separated by 'or'
    """

    search = forms.CharField(max_length=100, required=False, label="Free-form search", help_text="Use 'or' to search for multiple names")

    def filter(self, request, queryset):
        search = self.cleaned_data['search']
        if search == "":
            pass
        else:
            if search[:3] == '256':
                search = search[3:]
            elif search[:1] == '0':
                search = search[1:]
            queryset = queryset.exclude(
                connection__identity__in=Blacklist.objects.values_list('connection__identity', flat=True)
            ).filter(
                Q(name__icontains=search) |
                Q(reporting_location__name__icontains=search) |
                Q(connection__identity__icontains=search) |
                Q(schools__name__icontains=search)
            ).distinct()
        return queryset


class SchoolFilterForm(FilterForm):
    """ filter form for emis schools """
    def __init__(self):
        self.school = forms.ChoiceField(choices=(('', '-----'), (-1, 'Has No School'),) +\
                                       tuple(School.objects.filter(location__name__in=\
                                       EmisReporter.objects.values_list('reporting_location__name',flat=True)).values_list('pk', 'name').order_by('name')))

    def filter(self, request, queryset):
        school_pk = self.cleaned_data['school']
        if school_pk == '':
            return queryset
        elif int(school_pk) == -1:
            return queryset.filter(schools__name=None)
        else:
            return queryset.filter(schools=school_pk)

class LastReportingDateFilterForm(FilterForm):
    """ filter form for emis reporter on reporting date """
    from_date = forms.DateField()
    to_date = forms.DateField(help_text='select dates to filter by last reporting date')

    def filter(self, request, queryset):
        if self.cleaned_data['to_date'] is not None and self.cleaned_data['from_date'] is not None:
            if self.cleaned_data['to_date'] < self.cleaned_data['from_date']:
                return queryset.none()
            date_range = [self.cleaned_data['from_date'],self.cleaned_data['to_date']]
            if queryset.model.__name__ == 'EmisReporter':
                return queryset.filter(responses__date__range=date_range).distinct()
            if queryset.model.__name__ == 'Messages':
                return queryset.filter(date__range=date_range).distinct()

        return queryset

class PollFilterForm(FilterForm):
    """ filter form for message on polls """
    polls = forms.ChoiceField(choices=(('', '-----'),) + \
                                      tuple(Poll.objects.all().values_list('pk', 'name').order_by('name')))
    def filter(self, request, queryset):
        poll = Poll.objects.get(id = self.cleaned_data['polls'])
        if poll is not None:
            return queryset.filter(poll_responses__poll = poll)
        return queryset

class NewConnectionForm(forms.Form):
    identity = forms.CharField(max_length=15, required=True, label="Primary contact information")

class EditReporterForm(forms.ModelForm):
    class Meta:
        model = EmisReporter
        fields = ('name', 'gender', 'grade', 'reporting_location', 'groups', 'schools')

    def __init__(self, *args, **kwargs):
        super(EditReporterForm, self).__init__(*args, **kwargs)
        instance = kwargs['instance']
        data = kwargs.get('data')
        self.fields['reporting_location'] = forms.ModelChoiceField(queryset=Location.objects.filter(type='district').order_by('name'))

        if instance and data:
            edited_school = School.objects.none()
            schools_in_reporting_location = School.objects.filter(location=instance.reporting_location)
            if not is_empty(data.get('schools')):
                edited_school = School.objects.filter(pk = data.get('schools'))
            self.fields['schools'] = forms.ModelChoiceField(queryset=schools_in_reporting_location | edited_school)
        elif instance.reporting_location is None:
            if instance.schools.count() == 0:
                self.fields['schools'] = forms.ModelChoiceField(queryset=School.objects.none(),widget=forms.Select(attrs={'disabled':'disabled'}))
            else:
                self.fields['schools'] = forms.ModelChoiceField(queryset=instance.schools.all())
        else:
            schools_in_reporting_location = School.objects.filter(location=instance.reporting_location)
            if instance.schools.all().exists() and instance.schools.all()[0] not in schools_in_reporting_location:
                self.fields['schools'] = forms.ModelChoiceField(queryset=schools_in_reporting_location | instance.schools.all())
            else:
                self.fields['schools'] = forms.ModelChoiceField(queryset=schools_in_reporting_location)

        self.fields['schools'].required = False
        self.fields['gender'].required = False
        self.fields['grade'].required = False

    def clean(self):
        data = self.cleaned_data
        if data.get('schools') is not None and data['schools'].location != data.get('reporting_location'):
            self._errors['schools'] = self.error_class(['School should be from location same as reporting location'])
        return data

    def save(self, commit=True):
        reporter_form = super(EditReporterForm, self).save(commit=False)

        school = self.cleaned_data['schools']
        if school:
            schools = School.objects.filter(pk = school.pk)
            reporter_form.schools = schools
        else:
            # remove all schools associated with this reporter
            [reporter_form.schools.remove(sch) for sch in reporter_form.schools.all()]

        groups = self.cleaned_data['groups']
        if groups:
            reporter_form.groups.clear()
            group = Group.objects.get(pk = groups[0].pk)
            reporter_form.groups.add(group)
        else:
            [reporter_form.groups.remove(grp) for grp in reporter_form.groups.all()]

        if commit:
            reporter_form.save()


class DistrictFilterForm(forms.Form):
    def __init__(self):
        locs = Location.objects.filter(name__in=XFormSubmissionValue.objects.values_list('submission__connection__contact__reporting_location__name', flat=True))
        locs_list = []
        for loc in locs:
            if not Location.tree.root_nodes()[0].pk == loc.pk and loc.type.name == 'district':
                locs_list.append((loc.pk, loc.name))
        self.district = forms.ChoiceField(choices=(('', '-----'),) + tuple(locs_list))

class LimitedDistictFilterForm(FilterForm):
    """ filter Emis Reporters on their districts """
    def __init__(self):
        locs = Location.objects.filter(name__in=EmisReporter.objects.values_list('reporting_location__name',flat=True).distinct())
        locs_list = []
        for loc in locs:
            if not Location.tree.root_nodes()[0].pk == loc.pk and loc.type.name == 'district':
                locs_list.append((loc.pk, loc.name))
        self.district = forms.ChoiceField(choices=(('', '-----'),) + tuple(locs_list))

    def filter(self, request, queryset):
        district_pk = self.cleaned_data['district']
        if district_pk == '':
            return queryset
        elif int(district_pk) == -1:
            return queryset.filter(reporting_location=None)
        else:

            try:
                district = Location.objects.get(pk=district_pk)
            except Location.DoesNotExist:
                district = None
            if district:
                return queryset.filter(reporting_location__in=district.get_descendants(include_self=True))
            else:
                return queryset

class RolesFilterForm(FilterForm):
    def __init__(self, data=None, **kwargs):
        self.request = kwargs.pop('request')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)
        choices = ((-1, 'No Group'),) + tuple([(int(g.pk), g.name) for g in Group.objects.all().order_by('name')])
        self.fields['groups'] = forms.ChoiceField(choices=choices, required=True)


    def filter(self, request, queryset):
        groups_pk = self.cleaned_data['groups']
        if groups_pk == '-1':
            return queryset
        else:
            return queryset.filter(groups=groups_pk)

class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ('name', 'location')

    def __init__(self, *args, **kwargs):
        super(SchoolForm, self).__init__(*args, **kwargs)
        self.fields['location'] = forms.ModelChoiceField(queryset=Location.objects.filter(type='district').order_by('name'))


class FreeSearchSchoolsForm(FilterForm):
    """ concrete implementation of filter form
        TO DO: add ability to search for multiple search terms separated by 'or'
    """
    def __init__(self):
        self.search = forms.CharField(max_length=100, required=False, label="Free-form search",
                             help_text="Use 'or' to search for multiple names")

    def filter(self, request, queryset):
        search = self.cleaned_data['search']
        if search == "":
            return queryset
        else:
            return queryset.filter(Q(name__icontains=search)
                                   | Q(emis_id__icontains=search)
                                   | Q(location__name__icontains=search))

class SchoolDistictFilterForm(FilterForm):
    """ filter Schools on their districts """
    def __init__(self):
        locs = Location.objects.filter(name__in=School.objects.values_list('location__name', flat=True)).order_by('name')
        locs_list = []
        for loc in locs:
            if not Location.tree.root_nodes()[0].pk == loc.pk and loc.type.name == 'district':
                locs_list.append((loc.pk, loc.name))
        self.district = forms.ChoiceField(choices=(('', '-----'),) + tuple(locs_list))

    def filter(self, request, queryset):
        district_pk = self.cleaned_data['district']
        if district_pk == '':
            return queryset
        elif int(district_pk) == -1:
            return queryset.filter(reporting_location=None)
        else:

            try:
                district = Location.objects.get(pk=district_pk)
            except Location.DoesNotExist:
                district = None
            if district:
                return queryset.filter(location__in=district.get_descendants(include_self=True))
            else:
                return queryset


class ReportCommentForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.all(), widget = forms.HiddenInput())
    class Meta:
        model = ReportComment
    def __init__(self, *args, **kwargs):
        super(ReportCommentForm, self).__init__(*args, **kwargs)
        self.fields['report_date'].required = False
        self.fields['reporting_period'].required = False

    def save(self, commit=True):
        # do all that funky saving
        report_comment = super(ReportCommentForm, self).save(commit=False)
        reporting_period = self.cleaned_data.get('reporting_period','')
        today = datetime.datetime.now()

        if reporting_period == 'wk':
            report_comment.set_report_date(
                get_week_date(depth=2)[0][0]
            )
        elif reporting_period == 'mo':
            report_comment.set_report_date(
                get_month_day_range(today)[0]
            )
        elif reporting_period == 't':
            #TODO how best to set termly comments
            pass

        if commit:
            report_comment.save()
        return report_comment




class UserForm(forms.ModelForm):

    location=forms.ModelChoiceField(queryset=Location.objects.filter(type__in=["district","country"]).order_by('name'),required=True)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput,required=False)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput,
        help_text = "Enter the same password as above, for verification.",required=False)

    class Meta:
        model = User
        fields = ("username","first_name","last_name", "email", "groups","password1","password2")
    def __init__(self, *args, **kwargs):
        self.edit= kwargs.pop('edit', None)
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['groups'].help_text=""
        self.fields['groups'].required=True
        self.fields['email'].help_text = "Optional field"



    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        if not self.edit:
            raise forms.ValidationError("A user with that username already exists.")
        else:
            return username

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")

        password2 = self.cleaned_data.get("password2","")
        if password1 == password2 and password2 =="" and self.edit:
            return password2
        elif password2 =="":
            raise forms.ValidationError("This Field is Required")
        if password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        return password2

    def save(self, commit=True):
        user = super(UserForm, self).save(commit=False)
        if self.edit and self.cleaned_data["password1"] != "":
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class MassTextForm(ActionForm):

    text = forms.CharField(max_length=160, required=True, widget=SMSInput())
    action_label = 'Send Message'

    def clean_text(self):
        text = self.cleaned_data['text']

        #replace common MS-word characters with SMS-friendly characters
        for find, replace in [(u'\u201c', '"'),
                              (u'\u201d', '"'),
                              (u'\u201f', '"'),
                              (u'\u2018', "'"),
                              (u'\u2019', "'"),
                              (u'\u201B', "'"),
                              (u'\u2013', "-"),
                              (u'\u2014', "-"),
                              (u'\u2015', "-"),
                              (u'\xa7', "$"),
                              (u'\xa1', "i"),
                              (u'\xa4', ''),
                              (u'\xc4', 'A')]:
            text = text.replace(find, replace)
        return text

    def perform(self, request, results):

        if results is None or len(results) == 0:
            return ('A message must have one or more recipients!', 'error')

        if request.user and request.user.has_perm('auth.add_message'):
            connections = \
                list(Connection.objects.filter(contact__in=results).distinct())

            text = self.cleaned_data.get('text', "")
            text = text.replace('%', u'\u0025')

            messages = Message.mass_text(text, connections)

            MassText.bulk.bulk_insert(send_pre_save=False,
                    user=request.user,
                    text=text,
                    contacts=list(results))
            masstexts = MassText.bulk.bulk_insert_commit(send_post_save=False, autoclobber=True)
            masstext = masstexts[0]
            if settings.SITE_ID:
                masstext.sites.add(Site.objects.get_current())

            return ('Message successfully sent to %d numbers' % len(connections), 'success',)
        else:
            return ("You don't have permission to send messages!", 'error',)


class SchoolMassTextForm(ActionForm):

    text = forms.CharField(max_length=160, required=True, widget=SMSInput())
    action_label = 'Send Message'

    def clean_text(self):
        text = self.cleaned_data['text']

        #replace common MS-word characters with SMS-friendly characters
        for find, replace in [(u'\u201c', '"'),
                              (u'\u201d', '"'),
                              (u'\u201f', '"'),
                              (u'\u2018', "'"),
                              (u'\u2019', "'"),
                              (u'\u201B', "'"),
                              (u'\u2013', "-"),
                              (u'\u2014', "-"),
                              (u'\u2015', "-"),
                              (u'\xa7', "$"),
                              (u'\xa1', "i"),
                              (u'\xa4', ''),
                              (u'\xc4', 'A')]:
            text = text.replace(find, replace)
        return text

    def perform(self, request, results):
        if results is None or len(results) == 0:
            return ('A message must have one or more recipients!', 'error')

        if request.user and request.user.has_perm('auth.add_message'):
            reporters = []
            for school in results:
                for rep in school.emisreporter_set.filter(groups__name__in=['Teachers', 'Head Teachers']):
                    reporters.append(rep)
            connections = \
                list(Connection.objects.filter(contact__in=reporters).distinct())

            text = self.cleaned_data.get('text', "")
            text = text.replace('%', u'\u0025')

            messages = Message.mass_text(text, connections)

            MassText.bulk.bulk_insert(send_pre_save=False,
                    user=request.user,
                    text=text,
                    contacts=list(reporters))
            masstexts = MassText.bulk.bulk_insert_commit(send_post_save=False, autoclobber=True)
            masstext = masstexts[0]
            if settings.SITE_ID:
                masstext.sites.add(Site.objects.get_current())

            return ('Message successfully sent to %d numbers' % len(connections), 'success',)
        else:
            return ("You don't have permission to send messages!", 'error',)

class ScriptsForm(forms.ModelForm):
    date = forms.DateField(label="Schedule Date: ", widget=extras.widgets.SelectDateWidget(), required=False)
    class Meta:
        model = Script
        fields = ("slug", "name","enabled")
        widgets = {
            'slug': forms.HiddenInput(),
            'name': forms.TextInput(attrs={'size': 60}),
            'enabled':forms.CheckboxInput(attrs={'onclick':'check_clicked(this);'})
        }

class SearchForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['class'] = 'autocomplete'
    class Meta:
        model = Location
        fields = ('name',)

class ResultForm(forms.Form):
    from_date = forms.DateTimeField()
    to_date = forms.DateTimeField()
