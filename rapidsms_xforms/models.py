from threading import Lock
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db import connections, router, transaction, DEFAULT_DB_ALIAS
from eav.models import Attribute, Value
from eav import register
from eav.managers import EntityManager
from rapidsms.contrib.locations.models import Point
from rapidsms.models import Connection
import django.dispatch
import re
from django.template import Context, Template
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from rapidsms.models import ExtensibleModelBase
from eav.fields import EavSlugField

class XForm(models.Model):
    """
    An XForm, which is just a collection of fields.

    XForms also define their keyword which will be used when submitting via SMS.
    """
    PREFIX_CHOICES = (
        ('+','Plus (+)'),
        ('-','Dash (-)'),
    )
    SEPARATOR_CHOICES = (
        (',','Comma (,)'),
        (';','Semicolon (;)'),
        (':','Colon (:)'),
        ('*','Asterisk (*)'),
    )

    name = models.CharField(max_length=32,
                            help_text="Human readable name.")
    keyword = EavSlugField(max_length=32,
                           help_text="The SMS keyword for this form, must be a slug.")
    description = models.TextField(max_length=255,
                               help_text="The purpose of this form.")
    response = models.CharField(max_length=255,
                                help_text="The response sent when this form is successfully submitted.")
    active = models.BooleanField(default=True,
                                 help_text="Inactive forms will not accept new submissions.")

    command_prefix = models.CharField(max_length=1, choices=PREFIX_CHOICES, null=True, blank=True,default='+',
                                      help_text="The prefix required for optional field commands, defaults to '+'")

    keyword_prefix = models.CharField(max_length=1, choices=PREFIX_CHOICES, null=True, blank=True,
                                      help_text="The prefix required for form keywords, defaults to no prefix.")

    separator = models.CharField(max_length=1, choices=SEPARATOR_CHOICES, null=True, blank=True,
                                 help_text="The separator character for fields, field values will be split on this character.")

    owner = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    site = models.ForeignKey(Site)
    objects = models.Manager()
    on_site = CurrentSiteManager()

    unique_together = (("name", "site"), ("keyword", "site"))

    _original_keyword = None

    def __init__(self, *args, **kwargs):
        """
        We overload init so we can keep track of our original keyword.  This is because when
        the user changes the keyword we need to remap all the slugs for our fields as well.
        """
        super(XForm, self).__init__(*args, **kwargs)
        self.__original_keyword = self.keyword

    @classmethod
    def find_form(cls, message):
        """
        This method is responsible for find a matching XForm on this site given the passed in message.

        We do a few things to be agressive in matching the keyword, specifically:
            - if no exact matches are found for the keyword, we tests for levenshtein distance of <= 1
            - we also take into account each form's keyword prefix parameter

        The return value is the matched form, as well as the remainder of the message apart from the keyword
        """

        # first pass, match exactly
        matched = None
        for form in XForm.on_site.filter(active=True):
            remainder = form.parse_keyword(message, False)
            if not remainder is None:
                matched = form
                break

        # found it with an exact match, return it
        if matched:
            return matched

        matched = []
        for form in XForm.on_site.filter(active=True):
            remainder = form.parse_keyword(message, True)
            if remainder:
                matched.append(form)

        # if we found one and only one match using fuzzy matching, return it
        if len(matched) == 1:
            return matched[0]
        else:
            return None

    def parse_keyword(self, message, fuzzy=True):
        """
        Given a message, tries to parse the keyword for the form.  If it matches, then we return
        the remainder of the message, otherwise if the message doesn't start with our keyword then
        we return None
        """
        # remove leading and trailing whitespace
        message = message.strip()

        # empty string case
        if message.lower() == self.keyword.lower():
            return ""

        # our default regex to match keywords
        regex = "^[^0-9a-z]*([0-9a-z]+)[^0-9a-z](.*)"

        # modify it if there is a keyword prefix
        # with a keyword prefix of '+', we want to match cases like:
        #       +survey,  + survey, ++survey +,survey
        if self.keyword_prefix:
            regex = "^[^0-9a-z]*" + re.escape(self.keyword_prefix) + "+[^0-9a-z]*([0-9a-z]+)[^0-9a-z](.*)"

        # run our regular expression to extract our keyword
        match = re.match(regex, message, re.IGNORECASE)

        # if this in a format we don't understand, return nothing
        if not match:
            return None

        # by default only match things that are exact
        target_distance = 0
        if fuzzy:
            target_distance = 1

        keyword = match.group(1)
        if dl_distance(unicode(keyword.lower()), unicode(self.keyword.lower())) <= target_distance:
            return match.group(2)

        # otherwise, return that we don't match this message
        else:
            return None

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
                typedef = XFormField.lookup_type(field.field_type)
                values[field.command] = typedef['parser'](field.command, values[field.command])

        # create our submission now
        submission = self.submissions.create(type='odk-www', raw=xml)
        self.update_submission_from_dict(submission, values)

        return submission

    def process_import_submission(self, raw, connection, values):
        """
        Given a dict of values and the original row, import the data
        as a submission. Validates against contraints including checking
        for required fields.  Raises ValidationError if supplied could
        not be processed.
        """
        fields = self.fields.all()
        for field in fields:
            required=len(field.constraints.all().filter(type='req_val')) > 0
            if required and (field.command not in values or len(values[field.command]) == 0):
                raise ValidationError('Required field %s not supplied' % field.command)

            # pass it through our cleansing filter which will
            # check for type and any constraint validation
            # this raises ValidationError if it fails
            if field.command in values:
                field.clean_submission(values[field.command])

        # check if the values contain extra fields not in our form
        for command, value in values.items():            
            fields = self.fields.filter(command=command)
            if len(fields) != 1 and command != "connection":
                raise ValidationError("Could not resolve field for %s" % command)

        # resolve object types to their actual objects
        for field in self.fields.filter(datatype=XFormField.TYPE_OBJECT):
            if field.command in values:
                typedef = XFormField.lookup_type(field.field_type)
                values[field.command] = typedef['parser'](field.command, values[field.command])

        # create submission and update the values
        submission = self.submissions.create(type='import', raw=raw, connection=connection)
        self.update_submission_from_dict(submission, values)
        return submission

    def is_command(self, segment, commands):
        """
        Given a segment and commands dict, it checks if segment contains a command
        the we return that command if it's true, otherwise None
        """
        # no comamnd prefix, check whether this is a command word
        if not self.command_prefix:
            segment_word = segment
      
            if segment.find(' ') >= 0:
                # split the segment on spaces
                (segment_word, rest) = segment.split(' ', 1)
            
            if segment_word.lower() in commands:
                return segment_word

        # we do have a command prefix, and this word begins with it
        elif segment.startswith(self.command_prefix):
            return segment

        return None


    def parse_sms_submission(self, message):
        """
        sms submissions can have two formats, either explicitely marking each field:
            <keyword> +field_command1 [values] +field_command2 [values]
        
        or ommitting the 'command' for all required fields:
            <keyword> [first required field] [second required field] +field_command3 [first optional field]
        
        Note that if you are using the no-delimeter form, then all string fields are 'assumed' to be
        a single word.  TODO: this could probably be made to be smarter
        """

        # we'll return a hash of values and/or errors
        submission = {}
        values = []
        errors = []

        submission['values'] = values
        submission['message'] = message
        submission['has_errors'] = True
        submission['errors'] = errors

        # parse out our keyword
        remainder = self.parse_keyword(message)
        if remainder is None:
            errors.append(ValidationError("Incorrect keyword.  Keyword must be '%s'" % self.keyword))
            submission['response'] = "Incorrect keyword.  Keyword must be '%s'" % self.keyword
            return submission

        # separator mode means we don't split on spaces
        separator = None

        # if the separator is some non-whitespace character, and this form has only
        # one text-type field, the entire remainder can be considered its [command]-value pair
        if self.separator and self.separator.strip() and self.fields.count() == 1 and self.fields.all()[0].field_type == XFormField.TYPE_TEXT:
            segments = [remainder,]
        else:
            # figure out if we are using separators
            if self.separator and message.find(self.separator) >= 0:
                separator = self.separator

            # so first let's split on the separator passed in
            segments = remainder.split(separator)

        # remove any segments that are empty
        stripped_segments = []
        for segment in segments:
            segment = segment.strip()
            if segment:
                # also split any of these up by prefix, we could have a segment at this point
                # which looks like this:
                #      asdf+name emile+age 10
                # and which we want to turn it into three segments of:
                #      ['asdf', '+name emile', '+age 10']
                #
                if self.command_prefix:
                    prefix_index = segment.find(self.command_prefix)
                    while prefix_index > 0:
                        # take the left and right sides of the prefix
                        left = segment[0:prefix_index]
                        right = segment[prefix_index:]
                    
                        # append our left side to our list of stripped segments
                        stripped_segments.append(left.strip())
                    
                        # make the right side our new segment
                        segment = right.strip()
                    
                        # and see if it is worthy of stripping
                        prefix_index = segment.find(self.command_prefix)

                if segment:
                    stripped_segments.append(segment)

        segments = stripped_segments
        
        # build a dict of all our commands
        commands = dict()
        for field in self.fields.all():
            commands[field.command.lower()] = field

        # we first try to deal with required fields... we skip out of this processing either when
        # we reach a command prefix (+) or we have processed all required fields
        for field in self.fields.all().order_by('order', 'id'):
            required = field.constraints.all().filter(type="req_val")

            # no more text in the message, break out
            if not segments:
                break

            segment = segments.pop(0)

            # if this segment is a command
            if self.is_command(segment, commands):
                # pop it back on and break
                segments.insert(0, segment)
                break

            # ok, this looks like a valid required field value, clean it up
            try:
                cleaned = field.clean_submission(segment)
                values.append(dict(name=field.command, value=cleaned))
            except ValidationError as err:
                errors.append(err)
                break
            
        # for any remaining segments, deal with them as command / value pairings
        while segments:
            # search for our command
            command = None
            while segments:
                segment = segments.pop(0)

                # if this segment contains a command, set the segment as our command and 
                # parse this segment
                if self.is_command(segment, commands):
                    command = segment
                    break

            # no command found?  break out
            if not command:
                break

            # if there is a prefix, strip it off
            command = command.lower()
            if self.command_prefix:
                # strip off any leading junk from the command, cases that should work:
                #    ++age, +-age, +.age +++age
                match = re.match("^([^0-9a-z]*)(.*)$", command)
                command = match.group(2)

            # if there are spaces in the command, then split on that space, commands can't have spaces
            # so everything past the space must be part of the value
            if command.find(' ') >= 0:
                (command, value) = command.split(' ', 1)
                segments.insert(0, value)

            # now read in the value, basically up to the next command, joining segments
            # with spaces
            value = None
            while segments:
                segment = segments.pop(0)
                if self.is_command(segment, commands):
                    segments.insert(0, segment)
                    break

                # this isn't a command, but rather part of the value
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
                        # check for duplicate values
                        duplicate = False
                        for d in values:
                            if d['name'] == field.command:
                                duplicate = True
                                errors.append(ValidationError("Expected one value for %s, more than one was given." % field.description))                                
                                break
                        if not duplicate:
                            values.append(dict(name=field.command, value=cleaned))        
                    except ValidationError as err:
                        errors.append(err)

        # build a map of the number of values we have for each included field
        # TODO: for the love of god, someone show me how to do this in one beautiful Python 
        # lambda, just don't have time now
        value_count = {}
        value_dict = {}
        for value_pair in values:
            name = value_pair['name']
            value_dict[name] = value_pair['value']

            if name in value_count:
                value_count[name] += 1
            else:
                value_count[name] = 1

        # do basic sanity checks over all fields
        for field in self.fields.all():
            required_const = field.constraints.all().filter(type="req_val")
            # check that all required fields had a value set
            if required_const and field.command not in value_count:
                errors.append(ValidationError(required_const[0].message))
            # check that all fields actually have values
            if field.command in value_dict and not value_dict[field.command]:
                errors.append(ValidationError("Expected a value for %s, none given." % field.description))

        # no errors?  wahoo
        if not errors:
            submission['has_errors'] = False
            submission['response'] = self.response
        else:
            error = submission['errors'][0]
            if getattr(error, 'messages', None):
                submission['response'] = str(error.messages[0])
            else:
                submission['response'] = str(error)
            submission['has_errors'] = True

        return submission

    def build_template_vars(self, submission, sub_dict):
        """
        Given a submission builds the dict of values that will be available in the template.
        """
        template_vars = dict(confirmation_id=submission.confirmation_id)
        for field_value in sub_dict['values']:
            template_vars[field_value['name']] = field_value['value']

        return template_vars

    def build_template_response(self, response, template_vars):
        """
        Given a template string a dictionary of values, tries to compile the template and evaluate it.
        """
        # build our template
        template = Template("{% load messages %}" + response)

        context = Context(template_vars)
        return template.render(context)

    def process_sms_submission(self, message_obj):
        """
        Given an incoming SMS message, will create a new submission.  If there is an error
        we will throw with the appropriate error message.
        
        The newly created submission object will be returned.
        """
        message = message_obj.text
        connection = message_obj.connection
        # parse our submission
        sub_dict = self.parse_sms_submission(message)

        # create our new submission, we'll add field values as we parse them
        submission = XFormSubmission(xform=self, type='sms', raw=message, connection=connection)
        submission.save()

        # build our template response
        template_vars = self.build_template_vars(submission, sub_dict)
        sub_dict['response'] = self.build_template_response(sub_dict['response'], template_vars)

        # the values we've pulled out
        values = {}

        # for each of our values create the attribute
        for field_value in sub_dict['values']:
            field = XFormField.on_site.get(xform=self, command=field_value['name'])
            submission.values.create(attribute=field, value=field_value['value'], entity=submission)

        # if we had errors
        if sub_dict['has_errors']:
            # stuff them as a transient variable in our submission, our caller may message back
            submission.errors = sub_dict['errors']
            
            # and set our db state as well
            submission.has_errors = True
            submission.save()

        # set our transient response
        submission.response = sub_dict['response']
        # trigger our signal
        xform_received.send(sender=self, xform=self, submission=submission, message=message_obj)
        return submission

    def check_template(self, template):
        """
        Tries to compile and render our template to make sure it passes.
        """
        try:
            t = Template("{% load messages %}" + template)

            # we build a context that has dummy values for all required fields
            context = {}
            context['confirmation_id'] = 1
            for field in self.fields.all():
                required = field.constraints.all().filter(type="req_val")

                # we are at a field that isn't required?  pop out, these will be dealt with 
                # in the next block
                if not required:
                    continue

                if field.field_type == XFormField.TYPE_INT or field.field_type == XFormField.TYPE_FLOAT:
                    context[field.command] = "1"
                else:
                    context[field.command] = "test"

            t.render(Context(context))
        except Exception as e:
            raise ValidationError(str(e))

    def full_clean(self, exclude=None):
        self.check_template(self.response)
        return super(XForm, self).full_clean(exclude)

    def save(self, force_insert=False, force_update=False, using=None):
        """
        On saves we check to see if the keyword has changed, if so loading all our fields
        and resaving them to update their slugs.
        """
        self.check_template(self.response)

        super(XForm, self).save(force_insert, force_update, using)

        # keyword has changed, load all our fields and update their slugs
        # TODO, damnit, is this worth it?
        if self.keyword != self.__original_keyword:
            for field in self.fields.all():
                field.save(force_update=True, using=using)
                        
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
        dict( label='Integer', type=TYPE_INT, db_type=TYPE_INT, xforms_type='integer', parser=None ),
        dict( label='Decimal', type=TYPE_FLOAT, db_type=TYPE_FLOAT, xforms_type='decimal', parser=None ),
        dict( label='String', type=TYPE_TEXT, db_type=TYPE_TEXT, xforms_type='string', parser=None )
    ]

    xform = models.ForeignKey(XForm, related_name='fields')
    field_type = models.SlugField(max_length=8, null=True, blank=True)
    command = EavSlugField(max_length=32)
    order = models.IntegerField(default=0)

    objects = models.Manager()
    on_site = CurrentSiteManager()    

    class Meta:
        ordering = ('order', 'id')

    @classmethod
    def register_field_type(cls, field_type, label, parserFunc, db_type=TYPE_TEXT, xforms_type='string'):
        """
        Used to register a new field type for XForms.  You can use this method to build new field types that are
        available when building XForms.  These types may just do custom parsing of the SMS text sent in, then stuff
        those results in a normal core datatype, or they may lookup and reference completely custom attributes.

        Refer to GeoPoint implementation to see an example of the latter.

        Arguments are:
           label: The label used for this field type in the user interface
           field_type: A slug to identify this field type, must be unique across all field types
           parser: The function called to turn the raw string into the appropriate type, should take two arguments.
                   Takes two arguments, 'command', which is the command of the field, and 'value' the string value submitted.
           db_type: How the value will be stored in the database, can be one of: TYPE_INT, TYPE_FLOAT, TYPE_TEXT or TYPE_OBJECT
           xforms_type: The type as defined in an XML xforms specification, likely one of: 'integer', 'decimal' or 'string'

        """
        XFormField.TYPE_CHOICES.append(dict(type=field_type, label=label, 
                                            db_type=db_type, parser=parserFunc, xforms_type=xforms_type))

    @classmethod
    def lookup_type(cls, otype):
        for typedef in XFormField.TYPE_CHOICES:
            if otype == typedef['type']:
                return typedef

        raise ValidationError("Unable to find parser for field: '%s'" % otype)


    def derive_datatype(self):
        """
        We map our field_type to the appropriate data_type here.
        """
        # set our slug based on our command and keyword
        self.slug = "%s_%s" % (self.xform.keyword, EavSlugField.create_slug_from_name(self.command))

        typedef = self.lookup_type(self.field_type)

        if not typedef:
            raise ValidationError("Field '%s' has an unknown data type: %s" % (self.command, self.datatype))

        self.datatype = typedef['db_type']

    def full_clean(self, exclude=None):
        self.derive_datatype()
        return super(XFormField, self).full_clean(['datatype'])

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
            # integer
            if self.field_type == Attribute.TYPE_INT:
                try:
                    cleaned_value = int(value)
                except ValueError:
                    raise ValidationError("+%s parameter must be an even number." % self.command)

            # float
            elif self.field_type == Attribute.TYPE_FLOAT:
                try:
                    cleaned_value = float(value)
                except ValueError:
                    raise ValidationError("+%s parameter must be a number." % self.command)

            # string
            elif self.field_type == Attribute.TYPE_TEXT:
                cleaned_value = value.strip()

            # something custom, pass it to our parser
            else:
                typedef = XFormField.lookup_type(self.field_type)
                cleaned_value = typedef['parser'](self.command, value)

        # now check our actual constraints if any
        for constraint in self.constraints.order_by('order'):
            constraint.validate(value)
        
        return cleaned_value

    def xform_type(self):
        """
        Returns the XForms type for the field type.
        """
        typedef = self.lookup_type(self.field_type)
        if typedef:
            return typedef['xform_type']
        else:
            raise RuntimeError("Field type: '%s' not supported in XForms" % self.field_type)

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
            if value == None or value == '':
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
    confirmation_id = models.IntegerField(default=0)

    confirmation_lock = Lock()

    # transient, only populated when the submission first comes in
    errors = []

    def save(self, force_insert=False, force_update=False, using=None):
        """
        Assigns our confirmation id.  We increment our confirmation id's for each form 
        for every submission.  
        """
        # only create confirmation ids for submissions without errors and which don't already have one
        if not self.confirmation_id:
            try:
                XFormSubmission.confirmation_lock.acquire()
                last_confirmation = 0

                last_submission = self.xform.submissions.all().order_by('-confirmation_id')
                if last_submission and last_submission[0].confirmation_id:
                    last_confirmation = last_submission[0].confirmation_id

                self.confirmation_id = last_confirmation + 1
            finally:
                XFormSubmission.confirmation_lock.release()

        super(XFormSubmission, self).save(force_insert, force_update, using)

    def __unicode__(self): # pragma: no cover
        return "%s (%s) - %s" % (self.xform, self.type, self.raw)

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
    if len(coords) < 2:
        raise ValidationError("+%s parameter must be GPS coordinates in the format 'lat long'" % command)

    for coord in coords[0:2]:
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
    cleaned_value = Point.objects.create(latitude=coords[0], longitude=coords[1])
    return cleaned_value

# register geopoints as a type
XFormField.register_field_type(XFormField.TYPE_GEOPOINT, 'GPS Coordinate', create_geopoint,
                               xforms_type='geopoint', db_type=XFormField.TYPE_OBJECT)

# add a to_dict to Point, yay for monkey patching
def point_to_dict(self):
    return dict(name='coord', lat=self.latitude, lng=self.longitude)
Point.to_dict = point_to_dict

def dl_distance(s1, s2):
    """
    Computes the Damerau-Levenshtein distance between two strings.  Not the fastest implementation
    in the world, but works for our purposes.

    Ripped from: http://www.guyrutenberg.com/2008/12/15/damerau-levenshtein-distance-in-python/
    """
    d = {}
    lenstr1 = len(s1)
    lenstr2 = len(s2)
    for i in xrange(-1,lenstr1+1):
        d[(i,-1)] = i+1
    for j in xrange(-1,lenstr2+1):
        d[(-1,j)] = j+1
 
    for i in xrange(0,lenstr1):
        for j in xrange(0,lenstr2):
            if s1[i] == s2[j]:
                cost = 0
            else:
                cost = 1
            d[(i,j)] = min(
                           d[(i-1,j)] + 1, # deletion
                           d[(i,j-1)] + 1, # insertion
                           d[(i-1,j-1)] + cost, # substitution
                          )
            if i>1 and j>1 and s1[i]==s2[j-1] and s1[i-1] == s2[j]:
                d[(i,j)] = min (d[(i,j)], d[i-2,j-2] + cost) # transposition
 
    return d[lenstr1-1,lenstr2-1]




