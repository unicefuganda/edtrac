# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        #db.rename_column('locations_location', 'code', 'alias')
        db.rename_column('locations_location', 'is_active', 'status')
        db.add_column('locations_location', 'code', self.gf('django.db.models.fields.CharField')(max_length=100, null=True))
        db.add_column('locations_location', 'is_active', self.gf('django.db.models.fields.BooleanField')(default=True),keep_default=False)



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
