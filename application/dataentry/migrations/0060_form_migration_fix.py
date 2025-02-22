# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-08-07 15:06
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

from dataentry.models.form_migration import FormMigration

def migrate_forms(apps, schema_editor):
    # Invoke form migration with specific file containing lastest form data
    FormMigration.migrate(apps, schema_editor, 'form_data_20180816.json')

class Migration(migrations.Migration):


    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dataentry', '0059_auto_20180813_2109'),
    ]

    operations = [
        
        migrations.RunPython(migrate_forms),  
    ]
