import traceback
from optparse import OptionParser, make_option
from django.core.management.base import BaseCommand
import urllib2
from geoserver.models import PollData, PollCategoryData, PollResponseData
from poll.models import Poll
from rapidsms.contrib.locations.models import Location
from django.conf import settings

class Command(BaseCommand):

    help = """loads yes no polls into the poll data for geoserver"""

    def handle(self, **options):
        root = Location.tree.root_nodes()[0]
        yesno_category_name = ['yes', 'no', 'unknown']
        for p in Poll.objects.order_by('-pk')[0:9]:
            if p.categories.count():
                category_names = yesno_category_name if p.is_yesno_poll() else list(p.categories.all().values_list('name', flat=True))
                category_names.append('uncategorized')
                data = p.responses_by_category(location=root)
                insert_data = {}
                for d in data:
                    l = Location.objects.get(pk=d['location_id'])
                    insert_data.setdefault(l.code, {})
                    insert_data[l.code][d['category__name']] = d['value']
                for district_code, values in insert_data.items():
                    total = 0
                    for c in category_names:
                        values.setdefault(c, 0)

                    for cat_name, val in values.items():
                        total += val

                    top_category = 0
                    max_category = 0
                    cat_num = 0
                    # import pdb;pdb.set_trace()
                    print values
                    for cat_name in category_names:
                        values[cat_name] = float(values[cat_name]) / total
                        if values[cat_name] > max_category:
                            top_category = cat_num
                            max_category = values[cat_name]
                        cat_num += 1
                    import operator
                    top_category=category_names.index(max(values.iteritems(), key=operator.itemgetter(1))[0])
                    print max(values.iteritems(), key=operator.itemgetter(1))[0]
                    print top_category
                    if p.is_yesno_poll():
                        pd, _ = PollData.objects.using('geoserver').get_or_create(\
                            district=district_code,\
                            poll_id=p.pk,\
                            deployment_id=getattr(settings, 'DEPLOYMENT_ID', 1)
                        )
                        for c in category_names:
                            setattr(pd, c, values[c])
                        pd.save()
                    else:
                        description = "<br/>".join(["%s: %0.1f%%" % (cat_name,\
                                                                     (values[cat_name] * 100))\
                                                    for cat_name in category_names])
                        pd, _ = PollCategoryData.objects.using('geoserver').get_or_create(\
                            district=district_code,\
                            poll_id=p.pk,\
                            deployment_id=getattr(settings, 'DEPLOYMENT_ID', 1)
                        )
                        pd.description = description
                        pd.top_category = top_category
                        pd.save()
            else:
                pass
