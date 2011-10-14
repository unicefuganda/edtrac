
import traceback
from optparse import OptionParser, make_option
from django.core.management.base import BaseCommand
import urllib2
from geoserver.models import PollData

def add_poll_info(data_dict,poll):
    data=data_dict.get("data")
    for item in data:

        pd,created=PollData.objects.get_or_create(district=item["location_name"].upper(),poll=poll)
        print item.get("category__name")
        if item.get("category__name").strip() =="yes":
            pd.yes=item["value"]
        if item.get("category__name").strip() =="no":
            pd.no=item["value"]
        if item.get("category__name").strip() =="unknown":
            pd.unknown=item["value"]
        if item.get("category__name").strip() =="uncategorized":
            pd.uncategorized=item["value"]
        pd.poll=poll

        if pd.yes>pd.no:
            pd.dominant_category="yes"
        else:
            pd.dominant_category="no"
        pd.save()



class Command(BaseCommand):

    help = """loads yes no polls into the poll data for geoserver"""


    option_list = BaseCommand.option_list + (
    make_option("-p", "--poll", dest="poll"),

    )
    def handle(self, **options):
        poll=options["poll"]
        url="http://localhost:8000/polls/responses/%s/stats/1/"%(poll)
        try:

            response=urllib2.urlopen(url)

            if response.code==200:
                raw_data=response.read()
                data=eval(raw_data)
                add_poll_info(data,poll)
                print "successfully added poll info for districts!"
        except Exception, exc:
            print traceback.format_exc(exc)