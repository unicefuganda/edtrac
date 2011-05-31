import datetime
from django.http import HttpResponse
from django.db.models.query import QuerySet, ValuesQuerySet
from django.utils.text import capfirst
from  django.db.models.base import ModelBase
from rapidsms.models import  Backend
from django.conf import settings

def previous_calendar_week():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    return (start_date,end_date)


def previous_calendar_month():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)
    return (start_date,end_date)


def previous_calendar_quarter():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=90)
    return (start_date,end_date)

TIME_RANGES = {
    'w': previous_calendar_week,
    'm': previous_calendar_month,
    'q': previous_calendar_quarter

}


PREFIXES = [('70', 'warid'), ('75', 'zain'), ('71', 'utl'), ('', 'dmark')]

def assign_backend(number):
            if number.startswith('0'):
                number = '256%s' % number[1:]
            backendobj = None
            for prefix, backend in PREFIXES:
                if number[3:].startswith(prefix):
                    backendobj, created = Backend.objects.get_or_create(name=backend)
                    break
            return (number, backendobj)

class ExcelResponse(HttpResponse):
    def __init__(self,data, output_name='excel_report',headers=None,force_csv=False, encoding='utf8'):
        # Make sure we've got the right type of data to work with
        valid_data = False
        if hasattr(data, '__getitem__'):
            if isinstance(data[0], dict):
                if headers is None:
                    headers = data[0].keys()
                data = [[row[col] for col in headers] for row in data]
                data.insert(0, headers)
            if hasattr(data[0], '__getitem__'):
                valid_data = True
        import StringIO
        output = StringIO.StringIO()
        # Excel has a limit on number of rows; if we have more than that, make a csv
        use_xls = False
        if len(data) <= 65536 and force_csv is not True:
            try:
                import xlwt
            except ImportError:
                # xlwt doesn't exist; fall back to csv
                pass
            else:
                use_xls = True
        if use_xls:
            ##formatting of the cells
            # Grey background for the header row
            BkgPat = xlwt.Pattern()
            BkgPat.pattern = xlwt.Pattern.SOLID_PATTERN
            BkgPat.pattern_fore_colour = 22

            # Bold Fonts for the header row
            font = xlwt.Font()
            font.name = 'Calibri'
            font.bold = True

            # Non-Bold fonts for the body
            font0 = xlwt.Font()
            font0.name = 'Calibri'
            font0.bold = False

            # style and write field labels
            style = xlwt.XFStyle()
            style.font = font
            style.pattern = BkgPat

            style0 = xlwt.XFStyle()
            style0.font = font0
            book = xlwt.Workbook(encoding=encoding)
            sheet = book.add_sheet('Sheet 1')
            styles = {'datetime': xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
                      'date': xlwt.easyxf(num_format_str='yyyy-mm-dd'),
                      'time': xlwt.easyxf(num_format_str='hh:mm:ss'),
                      'default': style0,
                      'header':style}

            for rowx, row in enumerate(data):
                for colx, value in enumerate(row):
                    if isinstance(value, datetime.datetime):
                        cell_style = styles['datetime']
                    elif isinstance(value, datetime.date):
                        cell_style = styles['date']
                    elif isinstance(value, datetime.time):
                        cell_style = styles['time']
                    elif rowx==0:
                        cell_style = styles['header']
                    else:
                        cell_style = styles['default']

                    sheet.write(rowx, colx, value, style=cell_style)
            book.save(output)
            mimetype = 'application/vnd.ms-excel'
            file_ext = 'xls'
        else:
            for row in data:
                out_row = []
                for value in row:
                    if not isinstance(value, basestring):
                        value = unicode(value)
                    value = value.encode(encoding)
                    out_row.append(value.replace('"', '""'))
                output.write('"%s"\n' %
                             '","'.join(out_row))
            mimetype = 'text/csv'
            file_ext = 'csv'
        output.seek(0)
        super(ExcelResponse, self).__init__(content=output.getvalue(),
                                            mimetype=mimetype)

        self['Content-Disposition'] = 'attachment;filename="%s.%s"' % \
            (output_name.replace('"', '\"'), file_ext)
