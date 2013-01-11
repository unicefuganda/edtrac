# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db.utils import DatabaseError
from django.db import models
from django.db import transaction
from rapidsms.contrib.locations.models import Location
from django.db import connection

def db_table_field_exists(table_name,field):
    cursor=connection.cursor()
    return field in map(lambda x:  x[0].lower(),connection.introspection.get_table_description(cursor, table_name))

class Migration(DataMigration):

    def forwards(self, orm):
        #db.rename_column('locations_location', 'code', 'alias')
        try:
            db.rename_column('locations_location', 'is_active', 'status')
        except DatabaseError:
            transaction.rollback()

        try:
            if not db_table_field_exists("locations_location","code"):
                db.add_column('locations_location', 'code', self.gf('django.db.models.fields.CharField')(max_length=100, null=True))
        except DatabaseError:

            transaction.rollback()

        try:
            db.add_column('locations_location', 'is_active', self.gf('django.db.models.fields.BooleanField')(default=True),keep_default=False)
        except DatabaseError:
            transaction.rollback()




    def backwards(self, orm):
        #db.rename_column('locations_location', 'alias', 'code')
        db.rename_column('locations_location', 'status', 'is_active')



    models = {
        'geoserver.basicclasslayer': {
            'Meta': {'unique_together': "(('deployment_id', 'layer_id', 'district'),)", 'object_name': 'BasicClassLayer'},
            'deployment_id': ('django.db.models.fields.IntegerField', [], {'max_length': '3'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'district': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'layer_id': ('django.db.models.fields.IntegerField', [], {'max_length': '3'}),
            'style_class': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        'geoserver.emisattendencedata': {
            'Meta': {'object_name': 'EmisAttendenceData'},
            'boys': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'district': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'female_teachers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'girls': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'male_teachers': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'total_pupils': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'total_teachers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'geoserver.pollcategorydata': {
            'Meta': {'unique_together': "(('deployment_id', 'poll_id', 'district'),)", 'object_name': 'PollCategoryData'},
            'deployment_id': ('django.db.models.fields.IntegerField', [], {'max_length': '3'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'district': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'poll_id': ('django.db.models.fields.IntegerField', [], {}),
            'top_category': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'})
        },
        'geoserver.polldata': {
            'Meta': {'unique_together': "(('deployment_id', 'poll_id', 'district'),)", 'object_name': 'PollData'},
            'deployment_id': ('django.db.models.fields.IntegerField', [], {'max_length': '3'}),
            'district': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'no': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'poll_id': ('django.db.models.fields.IntegerField', [], {}),
            'uncategorized': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'unknown': ('django.db.models.fields.FloatField', [], {'default': '0', 'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'yes': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'})
        },
        'geoserver.pollresponsedata': {
            'Meta': {'unique_together': "(('deployment_id', 'poll_id', 'district'),)", 'object_name': 'PollResponseData'},
            'deployment_id': ('django.db.models.fields.IntegerField', [], {'max_length': '3'}),
            'district': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'percentage': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'poll_id': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['geoserver']
