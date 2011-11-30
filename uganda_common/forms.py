import datetime
from django import forms
from django.utils.safestring import mark_safe

class DateRangeForm(forms.Form): # pragma: no cover

    start = forms.IntegerField(required=True, widget=forms.HiddenInput())
    end = forms.IntegerField(required=True, widget=forms.HiddenInput())
    """
    This quick helper is used to create and sanitize the date range form (a widget).
    """
    start_ts = forms.IntegerField(required=True, widget=forms.HiddenInput())
    end_ts = forms.IntegerField(required=True, widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = self.cleaned_data

        start_ts = cleaned_data.get('start')
        cleaned_data['start_ts'] = datetime.datetime.fromtimestamp(float(start_ts) / 1000.0)

        end_ts = cleaned_data.get('end')
        cleaned_data['end_ts'] = datetime.datetime.fromtimestamp(float(end_ts) / 1000.0)
        return cleaned_data

class SMSInput(forms.Textarea):
    """ A widget for sms input """

    def __init__(self, *args, **kwargs):
        super(SMSInput, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        javascript = """
         <script type="text/javascript">
            //<![CDATA[
            function count_characters(elem,counter_container,submit_btn)
        {

        var elem= $(elem);
        var value = elem.val();
        var count = value.length;
        //regex for stripping the spaces
        var regex = new RegExp(/^\s*|\s*$/g);
        var chars_left = 160 - count;
        if (chars_left >= 0) {
          if (elem.is('.overlimit')) {
            elem.removeClass("overlimit");
          }

          if (chars_left > 1) {
            str = (chars_left) + " characters left";
          }
          else if (chars_left > 0) {
            str = "1 character left";
          }
          else {
            str = "No characters left";
          }
        } else {
          if (!elem.is('.overlimit')) {
            elem.addClass("overlimit");
          }

          if (chars_left < -1) {
            str = -chars_left + " characters over limit";
          }
          else {
            str = "1 character over limit";
          }
        }
        var ok = (count > 0 && count < 161) && (value.replace(regex,"") != elem._value);
        $(submit_btn).disabled = !ok;
        $(counter_container).html(str);
        }
        $('.smsinput').change(setInterval(function() {count_characters('.smsinput','.counter','foo');},500));
             //]]>
        </script>

        """
        style = """
        width: 18em;
        height: 56px;
        border: 1px solid #CCCCCC;
        color: #222222;
        font: 14px/18px "Helvetica Neue",Arial,sans-serif;
        outline: medium none;
        overflow-x: hidden;
        overflow-y: auto;
        padding: 2px;
        white-space: pre-wrap;
        word-wrap: break-word;

        """
        attrs = {'style':style}
        attrs['class'] = "smsinput"
        return mark_safe(
                "%s<div class='counter'></div>" % super(SMSInput, self).render(name, value, attrs) + javascript)
