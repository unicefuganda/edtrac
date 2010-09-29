from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from eav.models import Attribute, Value
from eav import register
from eav.managers import EntityManager
from rapidsms.contrib.locations.models import Point
from rapidsms.models import Connection
import django.dispatch
import re

class XForm(models.Model):
    """
    An XForm, which is just a collection of fields.

    XForms also define their keyword which will be used when submitting via SMS.
    """
    name = models.CharField(max_length=32, unique=True,
                            help_text="Human readable name.")
    keyword = models.SlugField(max_length=32, unique=True,
                               help_text="The SMS keyword for this form, must be a slug.")
    description = models.TextField(max_length=255,
                               help_text="The purpose of this form.")
    response = models.CharField(max_length=255,
                                help_text="The response sent when this form is successfully submitted.")
    active = models.BooleanField(default=True,
                                 help_text="Inactive forms will not accept new submissions.")

    owner = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def update_submission_from_dict(self, submission, values):
        """
        Sets the values for the passed in submission to the passed in dictionary.  The dict
        is expected to have keys corresponding to the commands of the fields.

        Note that the submission will set itself as no longer having any errors and trigger
        the xform_submitted signal

        TODO: I'm kind of putting all real logic in XForm as a base, but maybe this really
        belongs in XFormSubmission where I first had it.
        """
        # first update any existing values, removing them from our dict as we work
        for value in submission.values.all():
            # we have a new value, update it
            field = XFormField.objects.get(pk=value.attribute.pk)
            if field.command in values:
                value.value = values[field.command]
                value.save()
                del values[field.command]

            # no new value, we need to remove this one
            else:
                value.delete()
        # now add any remaining values in our dict
        for key, value in values.items():
            # look up the field by key
            field = XFormField.objects.get(xform=self, command=key)
            sub_value = submission.values.create(attribute=field, value=value, entity=submission)

        # clear out our error flag if there were some
        if submission.has_errors:
            submission.has_errors = False
            submission.save()

        # trigger our signal for anybody interested in form submissions
        xform_received.send(sender=self, xform=self, submission=submission)

    def process_odk_submission(self, xml, values):
        """
        Given the raw XML content and a map of values, processes a new ODK submission, returning the newly
        created submission.

        This mostly just coerces the 4 parameter ODK geo locations to our two parameter ones.
        """
        for field in self.fields.filter(datatype=XFormField.TYPE_OBJECT):
            if field.command in values:
                values[field.command] = XFormField.getParser(field)(field.command, values[field.command])

        # create our submission now
        submission = self.submissions.create(type='odk-www', raw=xml)
        self.update_submission_from_dict(submission, values)

        return submission

    def process_sms_submission(self, message, connection):
        """
        Given an incoming SMS message, will create a new submission.  If there is an error
        we will throw with the appropriate error message.
        
        The newly created submission object will be returned.
        """

        # sms submissions can have two formats, either explicitely marking each field:
        #    <keyword> +field_command1 [values] +field_command2 [values]
        #
        # or ommitting the 'command' for all required fields:
        #    <keyword> [first required field] [second required field] +field_command3 [first optional field]
        #
        # Note that if you are using the no-delimeter form, then all string fields are 'assumed' to be
        # a single word.  TODO: this could probably be made to be smarter

        # so first let's split on spaces
        segments = message.split(' ')

        # ignore everything before the first '+' that is the keyword and/or other data we
        # aren't concerned with
        segments = segments[1:]

        # the errors in this submission
        errors = []

        # create our new submission, we'll add field values as we parse them
        submission = XFormSubmission(xform=self, type='sms', raw=message, connection=connection)
        submission.save()
        # the values we have pulled out
        values = {}

        # we first try to deal with required fields... we skip out of this processing either when
        # we reach a +command delimeter or we have processed all required fields
        for field in self.fields.all().order_by('order', 'id'):
            required = field.constraints.all().filter(type="req_val")

            # we are at a field that isn't required?  pop out, these will be dealt with 
            # in the next block
            if not required:
                break

            # no more text in the message, break out
            if not segments:
                break

            segment = segments.pop(0)

            # segment starts with '+' this is actually a command
            if segment.startswith('+'):
                # push it back on our segments, it will be dealt with later
                segments.insert(0, segment)
                break
                
            # ok, this looks like a valid required field value, clean it up
            try:
                cleaned = field.clean_submission(segment)
                submission.values.create(attribute=field, value=cleaned, entity=submission)
                values[field.command] = cleaned
            except ValidationError as err:
                errors.append(err)
                break

        # for any remaining segments, deal with them as command / value pairings
        while segments:
            # search for our command
            command = None
            while segments:
                command = segments.pop(0)
                if command.startswith('+'):
                    break

            # no command found?  break out
            if not command:
                break

            command = command[1:].lower()

            # now read in the value, basically up to the next command, joining segments
            # with spaces
            value = None
            while segments:
                segment = segments.pop(0)
                if segment.startswith('+'):
                    segments.insert(0, segment)
                    break
                else:
                    if not value:
                        value = segment
                    else:
                        value += ' ' + segment

            # find the corresponding field, check its value and save it if it passes
            for field in self.fields.all():
                if field.command == command:
                    found = True

                    try:
                        cleaned = field.clean_submission(value)
                        submission.values.create(attribute=field, value=cleaned, entity=submission)
                        values[field.command] = cleaned
                    except ValidationError as err:
                        errors.append(err)

        # check that all required fields had a value set
        for field in self.fields.all():
            required_const = field.constraints.all().filter(type="req_val")
            if required_const and field.command not in values:
                errors.append(required_const[0].message)                

        # if we had errors
        if errors:
            # stuff them as a transient variable in our submission, our caller may message back
            submission.errors = errors
            
            # and set our db state as well
            submission.has_errors = True
            submission.save()

        # trigger our signal
        xform_received.send(sender=self, xform=self, submission=submission)

        return submission
                        
    def __unicode__(self): # pragma: no cover
        return self.name



class XFormField(Attribute):
    """
    A field within an XForm.  Fields can be one of the types:
        int: An integer
        dec: A decimal or float value
        str: A string
        gps: A lat and long pairing

    Note that when defining a field you must also define it's ``command`` which will
    be used to 'tag' the field in an SMS message.  ie: ``+age 10``

    """ 

    TYPE_INT = Attribute.TYPE_INT
    TYPE_FLOAT = Attribute.TYPE_FLOAT
    TYPE_TEXT = Attribute.TYPE_TEXT
    TYPE_OBJECT = Attribute.TYPE_OBJECT
    TYPE_GEOPOINT = 'geopoint'

    # These are the choices of types available for XFormFields.
    #
    # The first field is the field 'field_type'
    # The second is the label displayed in the XForm UI for this type
    # The third is the EAV datatype used for this type
    # And the last field is a method pointer to a parsing method which takes care of
    # deriving a field value from a string
    #
    # This list is manipulated when new fields are added at runtime via the register_field_type
    # hook.

    TYPE_CHOICES = [
        (TYPE_INT, 'Integer', TYPE_INT, None),
        (TYPE_FLOAT, 'Decimal', TYPE_FLOAT, None),
        (TYPE_TEXT, 'String', TYPE_TEXT, None),
    ]

    xform = models.ForeignKey(XForm, related_name='fields')
    field_type = models.SlugField(max_length=8, null=True, blank=True)
    command = models.SlugField(max_length=8)
    order = models.IntegerField(default=0)

    @classmethod
    def register_field_type(cls, field_type, name, parserFunc):
        XFormField.TYPE_CHOICES.append((field_type, name, XFormField.TYPE_OBJECT, parserFunc))

    @classmethod
    def lookup_parser(cls, otype):
        for (field_type, name, datatype, func) in XFormField.TYPE_CHOICES:
            if otype == field_type:
                return func

        raise ValidationError("Unable to find parser for field: '%s'" % otype)


    def derive_datatype(self):
        """
        We map our field_type to the appropriate data_type here.
        """
        if self.datatype:
            return

        for (field_type, name, datatype, func) in XFormField.TYPE_CHOICES:
            if field_type == self.field_type:
                self.datatype = datatype
                break

        if not self.datatype:
            raise ValidationError("Field '%s' has an unknown data type: %s" % (self.command, self.datatype))

    def full_clean(self, exclude=None):
        self.derive_datatype()
        return super(XFormField, self).full_clean(exclude)

    def save(self, force_insert=False, force_update=False, using=None):
        self.derive_datatype()
        return super(XFormField, self).save(force_insert, force_update, using)

    def clean_submission(self, value):
        """
        Takes the passed in string value and does two steps:

        1) tries to coerce the value into the appropriate type for the field.  This means changing
        a string to an integer or decimal, or splitting it into two for a gps location.

        2) if the coercion into the appropriate type succeeds, then validates then validates the
        value against any constraints on this field.  

        If either of these steps fails, a ValidationError is raised.  If both are successful
        then the cleaned, Python typed value is returned.
        """

        # this will be our properly Python typed value
        cleaned_value = None

        # check against our type first if we have a value
        if value is not None and len(value) > 0:
            if self.datatype == Attribute.TYPE_INT:
                try:
                    cleaned_value = int(value)
                except ValueError:
                    raise ValidationError("+%s parameter must be an even number." % self.command)

            if self.datatype == Attribute.TYPE_FLOAT:
                try:
                    cleaned_value = float(value)
                except ValueError:
                    raise ValidationError("+%s parameter must be a number." % self.command)


            # for gps, we expect values like 1.241 1.543, so basically two numbers
            if self.datatype == XFormField.TYPE_OBJECT:
                cleaned_value = XFormField.lookup_parser(self.field_type)(self.command, value)

            # anything goes for strings
            if self.datatype == Attribute.TYPE_TEXT:
                cleaned_value = value

        # now check our actual constraints if any
        for constraint in self.constraints.order_by('order'):
            constraint.validate(value)
        
        return cleaned_value

    def constraints_as_xform(self):
        """
        Returns the attributes for an xform bind element that corresponds to the
        constraints that are present on this field.

        See: http://www.w3.org/TR/xforms11/
        """

        # some examples:
        # <bind nodeset="/data/location" type="geopoint" required="true()"/>
        # <bind nodeset="/data/comment" type="string" constraint="(. &gt;  and . &lt; 100)"/>

        full = ""
        constraints = ""
        delim = ""

        for constraint in self.constraints.all():
            if constraint.type == 'req_val':
                full = "required=\"true()\""

            elif constraint.type == 'min_val':
                constraints += delim + ". &gt;= %s" % constraint.test
                delim = " and "

            elif constraint.type == 'max_val':
                constraints += delim + ". &lt;= %s" % constraint.test
                delim = " and "

            # hack in min and max length using regular expressions
            elif constraint.type == 'min_len':
                constraints += delim + "regex(., '^.{%s,}$')" % constraint.test
                delim = " and "

            elif constraint.type == 'max_len':
                constraints += delim + "regex(., '^.{0,%s}$')" % constraint.test
                delim = " and "
            
            elif constraint.type == 'regex':
                constraints += delim + "regex(., '%s')" % constraint.test
                delim = " and "

        if constraints:
            constraints = " constraint=\"(%s)\"" % constraints

        return "%s %s" % (full, constraints)


    def __unicode__(self): # pragma: no cover
        return self.name

CONSTRAINT_CHOICES = (
    ('min_val', 'Minimum Value'),
    ('max_val', 'Maximum Value'),
    ('min_len', 'Minimum Length'),
    ('max_len', 'Maximum Length'),
    ('req_val', 'Required'),
    ('regex', 'Regular Expression')
)

class XFormFieldConstraint(models.Model):
    """
    Constraint on a field.  A field can have 0..n constraints.  Constraints can be of
    the types:
        req_val: A value is required in every submission, though it can be an empty string
        min_val: The numerical value must be at least n
        max_val: The numerical value must be at most n
        min_len: The length of the value must be at least n
        max_len: The length of the value must be at most n
        regex: The value must match the regular expression

    All constraints also define an error message which will be returned if the constraint fails.

    Constraints are evaluated in order, the first constraint to fail shortcuts all subsequent 
    constraints.
    """


    field = models.ForeignKey(XFormField, related_name='constraints')
    
    type = models.CharField(max_length=10, choices=CONSTRAINT_CHOICES)
    test = models.CharField(max_length=255, null=True)
    message = models.CharField(max_length=100)
    order = models.IntegerField(default=1000)

    def validate(self, value):
        """
        Follows a similar pattern to Django's Form validation.  Validate takes a value and checks
        it against the constraints passed in.

        Throws a ValidationError if it doesn't meet the constraint.
        """

        if self.type == 'req_val':
            if not value:
                raise ValidationError(self.message)

        # if our value is None, none of these other constraints apply
        if value is None:
            return None

        # these two constraints depend on the value being numeric
        if self.type == 'min_val' or self.type == 'max_val':
            try:
                val = float(value)

                if self.type == 'min_val':
                    if float(value) < float(self.test):
                        raise ValidationError(self.message)

                elif self.type == 'max_val':
                    if float(value) > float(self.test):
                        raise ValidationError(self.message)

            except ValueError:
                raise ValidationError(self.message)

        # check our other constraints
        elif self.type == 'min_len':
            if len(value) < int(self.test):
                raise ValidationError(self.message)

        elif self.type == 'max_len':
            if len(value) > int(self.test):
                raise ValidationError(self.message)

        elif self.type == 'regex':
            if not re.match(self.test, value, re.IGNORECASE):
                raise ValidationError(self.message)

        return value

    def __unicode__(self): # pragma: no cover
        return "%s (%s)" % (self.type, self.test)


SUBMISSION_CHOICES = (
    ('www', 'Web Submission'),
    ('sms', 'SMS Submission'),
    ('odk-www', 'ODK Web Submission'),
    ('odk-sms', 'ODK SMS Submission')
)

class XFormSubmission(models.Model):
    """
    Represents an XForm submission.  This acts as an aggregator for the values and a way of 
    storing where the submission came form.
    """

    xform = models.ForeignKey(XForm, related_name='submissions')
    type = models.CharField(max_length=8, choices=SUBMISSION_CHOICES)
    connection = models.ForeignKey(Connection, null=True)
    raw = models.TextField()
    has_errors = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    # transient, only populated when the submission first comes in
    errors = []

    def __unicode__(self): # pragma: no cover
        return "%s (%s)" % (self.xform, self.type)

# This sets up XForm as an EAV-able model (its attributes will in fact be
# XFormFields
register(XFormSubmission)

class XFormSubmissionValue(Value):
    """
    Stores a value for a field that was submitted.  Note that this is a rather inelegant
    representation of the data, in that nothing is typed.  This is by design.  It isn't
    the job of XForms to store your cannonical version of the data, only to allow easy
    collection and validation.
    """

    submission = models.ForeignKey(XFormSubmission, related_name='values')

    def cleaned(self):
        return self.field.clean_submission(self.value)
    
    def value_formatted(self):
        """
        Returns a nicer version of our value, mostly just shortening decimals to be more sane.
        """
        if self.field.type == Attribute.TYPE_FLOAT:
            return "%.2f" % (self.cleaned())
        else:
            return self.value

    def __unicode__(self): # pragma: no cover
        return "%s=%s" % (self.attribute, self.value)


# Signal triggered whenever an xform is received.  The caller can derive from the submission
# whether it was successfully parsed or not and do what they like with it.

xform_received = django.dispatch.Signal(providing_args=["xform", "submission"])

def create_geopoint(command, value):
    """
    Used by our arbitrary field saving / lookup.  This takes the command and the string value representing
    a geolocation and return a Point location.
    """
    coords = value.split(' ')
    if len(coords) != 2:
        raise ValidationError("+%s parameter must be GPS coordinates in the format 'lat long'" % command)

    for coord in coords:
        try:
            test = float(coord)
        except ValueError:
            raise ValidationError("+%s parameter must be GPS coordinates the format 'lat long'" % command)
        
    # lat needs to be between -90 and 90
    if float(coords[0]) < -90 or float(coords[0]) > 90:
        raise ValidationError("+%s parameter has invalid latitude, must be between -90 and 90" % command)
        
    # lng needs to be between -180 and 180
    if float(coords[1]) < -180 or float(coords[1]) > 180:
        raise ValidationError("+%s parameter has invalid longitude, must be between -180 and 180" % command)

    # our cleaned value is the coordinates as a tuple
    cleaned_value = Point.objects.create(longitude=coords[0], latitude=coords[1])
    return cleaned_value

# register geopoints as a type
XFormField.register_field_type(XFormField.TYPE_GEOPOINT, 'GPS Coordinate', create_geopoint)



