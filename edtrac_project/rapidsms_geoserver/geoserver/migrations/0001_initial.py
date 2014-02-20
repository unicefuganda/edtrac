# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'PollData'
        db.create_table('geoserver_polldata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('district', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('poll_id', self.gf('django.db.models.fields.IntegerField')()),
            ('deployment_id', self.gf('django.db.models.fields.IntegerField')(max_length=3)),
            ('yes', self.gf('django.db.models.fields.FloatField')(default=0, null=True, blank=True)),
            ('no', self.gf('django.db.models.fields.FloatField')(default=0, null=True, blank=True)),
            ('uncategorized', self.gf('django.db.models.fields.FloatField')(default=0, null=True, blank=True)),
            ('unknown', self.gf('django.db.models.fields.FloatField')(default=0, max_length=5, null=True, blank=True)),
        ))
        db.send_create_signal('geoserver', ['PollData'])

        # Adding unique constraint on 'PollData', fields ['deployment_id', 'poll_id', 'district']
        db.create_unique('geoserver_polldata', ['deployment_id', 'poll_id', 'district'])

        # Adding model 'PollCategoryData'
        db.create_table('geoserver_pollcategorydata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('district', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('poll_id', self.gf('django.db.models.fields.IntegerField')()),
            ('deployment_id', self.gf('django.db.models.fields.IntegerField')(max_length=3)),
            ('top_category', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('geoserver', ['PollCategoryData'])

        # Adding unique constraint on 'PollCategoryData', fields ['deployment_id', 'poll_id', 'district']
        db.create_unique('geoserver_pollcategorydata', ['deployment_id', 'poll_id', 'district'])

        # Adding model 'PollResponseData'
        db.create_table('geoserver_pollresponsedata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('district', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('poll_id', self.gf('django.db.models.fields.IntegerField')()),
            ('deployment_id', self.gf('django.db.models.fields.IntegerField')(max_length=3)),
            ('percentage', self.gf('django.db.models.fields.FloatField')(default=0, null=True, blank=True)),
        ))
        db.send_create_signal('geoserver', ['PollResponseData'])

        # Adding unique constraint on 'PollResponseData', fields ['deployment_id', 'poll_id', 'district']
        db.create_unique('geoserver_pollresponsedata', ['deployment_id', 'poll_id', 'district'])

        # Adding model 'BasicClassLayer'
        db.create_table('geoserver_basicclasslayer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('district', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('style_class', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('deployment_id', self.gf('django.db.models.fields.IntegerField')(max_length=3)),
            ('layer_id', self.gf('django.db.models.fields.IntegerField')(max_length=3)),
            ('description', self.gf('django.db.models.fields.TextField')(default='')),
        ))
        db.send_create_signal('geoserver', ['BasicClassLayer'])

        # Adding unique constraint on 'BasicClassLayer', fields ['deployment_id', 'layer_id', 'district']
        db.create_unique('geoserver_basicclasslayer', ['deployment_id', 'layer_id', 'district'])

        # Adding model 'EmisAttendenceData'
        db.create_table('geoserver_emisattendencedata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('district', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('boys', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('girls', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('total_pupils', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('female_teachers', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('male_teachers', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('total_teachers', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('geoserver', ['EmisAttendenceData'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'BasicClassLayer', fields ['deployment_id', 'layer_id', 'district']
        db.delete_unique('geoserver_basicclasslayer', ['deployment_id', 'layer_id', 'district'])

        # Removing unique constraint on 'PollResponseData', fields ['deployment_id', 'poll_id', 'district']
        db.delete_unique('geoserver_pollresponsedata', ['deployment_id', 'poll_id', 'district'])

        # Removing unique constraint on 'PollCategoryData', fields ['deployment_id', 'poll_id', 'district']
        db.delete_unique('geoserver_pollcategorydata', ['deployment_id', 'poll_id', 'district'])

        # Removing unique constraint on 'PollData', fields ['deployment_id', 'poll_id', 'district']
        db.delete_unique('geoserver_polldata', ['deployment_id', 'poll_id', 'district'])

        # Deleting model 'PollData'
        db.delete_table('geoserver_polldata')

        # Deleting model 'PollCategoryData'
        db.delete_table('geoserver_pollcategorydata')

        # Deleting model 'PollResponseData'
        db.delete_table('geoserver_pollresponsedata')

        # Deleting model 'BasicClassLayer'
        db.delete_table('geoserver_basicclasslayer')

        # Deleting model 'EmisAttendenceData'
        db.delete_table('geoserver_emisattendencedata')


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
