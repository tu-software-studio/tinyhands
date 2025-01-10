import csv
import json
import requests
import traceback
from datetime import date
from django.db import transaction, IntegrityError
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from dataentry.models import Country, Form, LocationForm, VdfCommon


def field_has_data(field_value):
    if field_value is None or field_value == '' or field_value == '-':
        result = False
    else:
        result = True
    return result

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('country', nargs='+', type=str)
        parser.add_argument('from_form', nargs='+', type=str)
        parser.add_argument('to_form', nargs='+', type=str)

    def update_forms(self, country, from_form, to_form):
        stations = from_form.stations.filter(operating_country=country)
        for station in stations:
            to_form.stations.add(station)
        for station in stations:
            from_form.stations.remove(station)

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

        self.update_forms(country, from_form, to_form)



    def migrate_lfCommon202409(self, country, from_form, to_form):
        lfs = LocationForm.objects.filter(station__operating_country=country)
        for lf in lfs:
            lf_modified = False
            description_match = False

            for info in lf.locationinformation_set.all():
                info_modified = False
                merge_description = False
                if not description_match:
                    # First info where description matches merged description
                    # if description in info is updated then update merged description
                    description_match = info.description == lf.merged_description
                    merge_description = description_match

                # Append descriptive fields not in the new version to the description field
                for field_name in ['location_in_town', 'color', 'number_of_levels', 'nearby_landmarks']:
                    value = getattr(info, field_name)
                    if field_has_data(value):
                        info_modified = True
                        if field_has_data(info.description):
                            info.description = info.description + '\n' + field_name + ':' + value
                        else:
                            info.description = field_name + ':' + value

                if merge_description and info_modified:
                    lf.merge_description = info.description
                    lf_modified = True

                if field_has_data(info.suspects_associative):
                    info.suspects_associative = info.suspects_associative.replace(';',', ')
                    info_modified = True
                if field_has_data(info.persons_in_charge):
                    info_modified = True
                    if field_has_data(info.suspects_associative):
                        info.suspects_associative = (info.suspects_associative + '\nPerson in charge:' +
                                                     info.persons_in_charge.replace(';',', '))
                    else:
                        info.suspects_associative = 'Person in charge:' + info.persons_in_charge.replace(';',', ')
                if field_has_data(info.pvs_visited):
                    info.pvs_visited = info.pvs_visited.replace(';',', ')
                    info_modified = True

                if info_modified:
                    info.save()

            if lf_modified:
                lf.save()

        self.update_forms(country, from_form, to_form)

    def handle(self, *args, **options):
        country_name = options['country'][0]
        from_form_name = options['from_form'][0]
        to_form_name = options['to_form'][0]

        country = Country.objects.get(name=country_name)
        from_form = Form.objects.get(form_name=from_form_name)
        to_form = Form.objects.get(form_name=to_form_name)

        already_converted = to_form.stations.filter(operating_country=country)
        if len(already_converted) > 0:
            print('There are already ' + str(len(already_converted)) + ' projects in ' + country_name +
                  ' configured with form ' + to_form_name)
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