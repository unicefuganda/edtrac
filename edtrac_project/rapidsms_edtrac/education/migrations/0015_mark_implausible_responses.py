# -*- coding: utf-8 -*-
from south.v2 import DataMigration
from education.models import Response


class Migration(DataMigration):

    def forwards(self, orm):
        implausibles = Response.objects.filter(has_errors=False,
                                               message__direction='I',
                                               eav_values__value_float__gt=5000) \
                                       .update(has_errors=True)


    def backwards(self, orm):
        originals = Response.objects.filter(has_errors = True,
                                            message__direction='I',
                                            eav_values__value_float__gt = 5000) \
                                    .update(has_errors=False)
