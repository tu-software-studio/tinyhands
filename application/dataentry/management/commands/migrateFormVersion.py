import csv
import json
import requests
import traceback
from datetime import date
from django.db import transaction, IntegrityError
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from dataentry.models import Country, Form, LocationForm, Suspect, SuspectLegalPv, VdfCommon


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

    def add_checkbox_group(self, existing, new_value):
        if existing is None or existing == '':
            return new_value
        else:
            return existing + ';' + new_value

    def migrate_sfCommon202409(self, country, from_form, to_form):
        address_none = {'value': None}
        sfs = Suspect.objects.filter(station__operating_country=country)
        for sf in sfs:
            associations = sf.suspectassociation_set.all()
            for association in associations:
                modified = False
                if association.associated_pvs is not None and len(association.associated_pvs) > 0:
                    association.associated_pvs = association.associated_pvs.replace(';',', ')
                if association.associated_suspects is not None and len(association.associated_suspects) > 0:
                    association.associated_suspects = association.associated_suspects.replace(';', ', ')
                association.save()

            legal_list = sf.suspectlegal_set.all()
            for legal in legal_list:  # should be only one
                new_location_attempt = ''
                if legal.location_attempt is not None and len(legal.location_attempt) > 0:
                    attempt = legal.location_attempt.split(';')

                    if 'In Police Custody' in attempt:
                        new_location_attempt = self.add_checkbox_group(new_location_attempt,
                                                                       'In police custody')
                if (legal.location_last_address is not None and legal.location_last_address != address_none and
                        legal.location_last_address != ''):
                    new_location_attempt = self.add_checkbox_group(new_location_attempt,'Last known location')
                if legal.location_unable is not None and len(legal.location_unable) > 0:
                    unable = legal.location_unable.split(';')
                    if 'Insufficient Suspect Bio Details' not in unable:
                        new_location_attempt = self.add_checkbox_group(new_location_attempt,
                                                                       'Sufficient biographical details to identify the suspect')
                legal.location_attempt = new_location_attempt

                new_police_attempt = ''
                if legal.police_attempt == 'True':
                    new_police_attempt = self.add_checkbox_group(new_police_attempt, 'Yes')
                if legal.police_unable is not None and len(legal.police_unable) > 0:
                    unable = legal.police_unable.split(';')
                    if 'No' in unable:
                        new_police_attempt = self.add_checkbox_group(new_police_attempt,"No")
                    if 'Police say not enough evidence' in unable:
                        new_location_attempt = self.add_checkbox_group(new_police_attempt,
                                                                       "Police say not enough evidence")
                legal.police_attempt = new_police_attempt
                legal.save()

                suspect_pv = SuspectLegalPv()
                suspect_pv.suspect = sf
                suspect_pv.incident = legal.incident
                suspect_pv.pv_name = "Unspecified"
                if legal.pv_attempt is not None and len(legal.pv_attempt) > 0:
                    suspect_pv.willing_to_file = self.add_checkbox_group(suspect_pv.willing_to_file, 'Yes, willing')
                if legal.pv_unable is not None:
                    unable = legal.pv_unable.split(';')
                    if 'No' in unable:
                        suspect_pv.willing_to_file = self.add_checkbox_group(suspect_pv.willing_to_file,
                                                                              'Not willing to file a case at all')
                    if "Couldn't reestablish contact with PV" in unable:
                        suspect_pv.willing_to_file = self.add_checkbox_group(suspect_pv.willing_to_file,
                                                                             "Couldn’t establish contact with PV")
                    if "PV afraid for reputation" in unable:
                        suspect_pv.hesitation_concern = self.add_checkbox_group( suspect_pv.hesitation_concern,
                                                                                 "Afraid for reputation")
                    if "PV afraid for their safety" in unable:
                        suspect_pv.hesitation_concern = self.add_checkbox_group(suspect_pv.hesitation_concern,
                                                                                "Afraid for their safety")
                    if "PVs don't believe they were being trafficked" in unable:
                        suspect_pv.hesitation_concern = self.add_checkbox_group(suspect_pv.hesitation_concern,
                                                                                "Don’t believe they were being trafficked")
                    if "PV family not willing" in unable:
                        suspect_pv.hesitation_concern = self.add_checkbox_group(suspect_pv.hesitation_concern,
                                                                                "Family not willing")
                suspect_pv.save()

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