import csv
import json
import requests
import traceback
from datetime import date
from django.db import transaction, IntegrityError
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from dataentry.models import Country, Form, VdfCommon


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('country', nargs='+', type=str)
        parser.add_argument('from_form', nargs='+', type=str)
        parser.add_argument('to_form', nargs='+', type=str)
    
    def migrate_pvfCommon202408(self, country, from_form, to_form):
        print ('Begin migration for', country.name)
        pvfs = VdfCommon.objects.filter(station__operating_country=country)
        for pvf in pvfs:
            modified = False
            if pvf.share_gospel_film or pvf.share_gospel_tract or pvf.share_gospel_oral or pvf.share_gospel_other:
                pvf.share_gospel_resouce = True
                modified = True
            
            if pvf.how_pv_released == 'Someone came to pick the PV up from the station/shelter':
                pvf.how_pv_released = 'Someone came to station/shelter to pick up the PV'
                modified = True
            
            if pvf.overnight_lodging == 'Yes':
                pvf.overnight_lodging = 'True'
                modified = True
            elif pvf.overnight_lodging is not None:
                pvf.overnight_lodging = 'False'
                modified = True
            
            if modified:
                pvf.save()
        
        stations = from_form.stations.filter(operating_country=country)
        for station in stations:
            to_form.stations.add(station)
        for station in stations:
            from_form.stations.remove(station)
    
    
    def handle(self, *args, **options):
        country_name = options['country'][0]
        from_form_name = options['from_form'][0]
        to_form_name = options['to_form'][0]
        
        country = Country.objects.get(name=country_name)
        from_form = Form.objects.get(form_name=from_form_name)
        to_form = Form.objects.get(form_name=to_form_name)
        
        already_converted = to_form.stations.filter(operating_country=country)
        if len(already_converted) > 0:
            print('There are already ' + str(len(already_converted)) + ' projects in ' + country_name + ' configured with form ' + to_form_name)
            print('Migration cannot proceed')
            return
        
        to_convert = from_form.stations.filter(operating_country=country)
        if len(to_convert) < 1:
            print('There are no projects in ' + country_name + ' configured with form ' + from_form_name)
            print('Migration cannot proceed')
            return
        
        method = getattr(self, 'migrate_' + to_form_name)
        with transaction.atomic():
            method(country, from_form, to_form)