
import traceback
from optparse import OptionParser, make_option
from django.core.management.base import BaseCommand
import urllib2
from geoserver.models import PollData
from poll.models import Poll
from rapidsms.contrib.locations.models import Location

def add_poll_info(data_dict, poll):
    data = data_dict.get("data")
    for item in data:

        pd, created = PollData.objects.get_or_create(district=item["location_name"].upper(), poll=poll)
        print item.get("category__name")
        if item.get("category__name").strip() == "yes":
            pd.yes = item["value"]
        if item.get("category__name").strip() == "no":
            pd.no = item["value"]
        if item.get("category__name").strip() == "unknown":
            pd.unknown = item["value"]
        if item.get("category__name").strip() == "uncategorized":
            pd.uncategorized = item["value"]
        pd.poll = poll

        if pd.yes > pd.no:
            pd.dominant_category = "yes"
        else:
            pd.dominant_category = "no"
        pd.save()



class Command(BaseCommand):

    help = """loads yes no polls into the poll data for geoserver"""

    def is_yesno_poll(self, poll):
        return poll.categories.count() == 3 and \
            poll.categories.filter(name='yes').count() and \
            poll.categories.filter(name='no').count() and \
            poll.categories.filter(name='unknown').count()

    def handle(self, **options):
        root = Location.tree.root_nodes()[0]
        yesno_category_name = ['yes', 'no', 'unknown', 'uncategorized']
        for p in Poll.objects.exclude(categories=None):
            if self.is_yesno_poll(p):
                data = p.responses_by_category(location=root)
                insert_data = {}
                for d in data:
                    l = Location.objects.get(pk=d['location_id'])
                    insert_data.setdefault(l.code, {})
                    insert_data[l.code][d['category__name']] = d['value']
                for district_code, values in insert_data.items():
                    total = 0
                    for c in yesno_category_name:
                        values.setdefault(c, 0)

                    for cat_name, val in values.items():
                        total += val
                    for cat_name in values.keys():
                        values[cat_name] = float(values[cat_name]) / total
                    p.save(using='geoserver')
                    pd = PollData.objects.using('geoserver').get_or_create(\
                            district=l.code, \
                            poll=p, \
                            # FIXME add deployment_id
                            )
                    for c in yesno_category_name:
                        setattr(pd, c, values[c])
                    pd.save()
