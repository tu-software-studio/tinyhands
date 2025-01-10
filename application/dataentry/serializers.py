import datetime
import json

from rest_framework import serializers
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist

from dataentry.models import Address1, Address2, Region, Country, SiteSettings, InterceptionRecord, VictimInterview, BorderStation, MasterPerson, Person
from dataentry.models import Interceptee, InterceptionAlert, Permission, PermissionGroup, UserLocationPermission, Form, FormType, PersonAddress, PersonPhone, PersonSocialMedia, PersonDocument, PersonForm
from dataentry.models import AddressType, DocumentType, PhoneType, SocialMediaType, PersonIdentification
from dataentry.models import StationStatistics, LocationStatistics, LocationStaff, CountryExchange
from dataentry.models import PendingMatch, Audit, AuditSample, LegalCase, LegalCaseSuspect, LegalCaseVictim
from dataentry.models import GospelVerification
from dataentry.models import ClientDiagnostic
from dataentry.models import ProjectCategory
from dataentry.models import Empowerment
from dataentry.models import Gospel
from dataentry.models import Incident
from static_border_stations.serializers import LocationSerializer
from dataentry.form_data import FormData

from .helpers import related_items_helper

class Address1Serializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Address1


class Address1RelatedItemsSerializer(Address1Serializer):
    related_items = serializers.SerializerMethodField()
    get_related_items = related_items_helper

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Region

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Country

class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = SiteSettings


class CanonicalNameSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'name']
        model = Address2


class Address2Serializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Address2
        depth = 1

    def create(self, validated_data):
        found_address1 = Address1.objects.get(pk=self.context['request'].data['address1']['id'])
        if self.context['request'].data['canonical_name']['id'] == -1:
            found_address2 = None
        else:
            found_address2 = Address2.objects.get(pk=self.context['request'].data['canonical_name']['id'])
        validated_data['address1'] = found_address1
        validated_data['canonical_name'] = found_address2
        return Address2.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.address1 = Address1.objects.get(pk=self.context['request'].data['address1']['id'])
        instance.name = validated_data.get('name', instance.name)
        if self.context['request'].data['canonical_name']['id'] == -1:
            instance.canonical_name = None
        else:
            instance.canonical_name = Address2.objects.get(pk=self.context['request'].data['canonical_name']['id'])
        instance.latitude = validated_data.get('latitude', instance.latitude)
        instance.longitude = validated_data.get('longitude', instance.longitude)
        instance.level = validated_data.get('level', instance.level)
        instance.verified = validated_data.get('verified', instance.verified)
        instance.save()
        return instance

    canonical_name = CanonicalNameSerializer(required=False)
    address1 = Address1Serializer()


class Address2RelatedItemsSerializer(Address2Serializer):
    related_items = serializers.SerializerMethodField()
    get_related_items = related_items_helper


class BorderStationSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = BorderStation

    country_name = serializers.SerializerMethodField(read_only=True)
    country_currency = serializers.SerializerMethodField(read_only=True)
    number_of_interceptions = serializers.SerializerMethodField(read_only=True)
    number_of_staff = serializers.SerializerMethodField(read_only=True)
    ytd_interceptions = serializers.SerializerMethodField(read_only=True)
    location_set = LocationSerializer(many=True, read_only=True)
    project_category_name = serializers.SerializerMethodField(read_only=True)
    
    def get_interceptee_class(self, obj):
        interceptee_class = None
        form = FormData.find_form('IRF', obj.id)
        if form is not None:
            interceptee_class = FormData.get_form_card_class(form, 'People')
        
        return interceptee_class

    def get_number_of_interceptions(self, obj):
        interceptee_class = self.get_interceptee_class(obj)
        if interceptee_class is not None:
            return interceptee_class.objects.filter(interception_record__station=obj, person__role='PVOT').count()
        else:
            return 0

    def get_number_of_staff(self, obj):
        return obj.staff_set.all().count()

    def get_ytd_interceptions(self, obj):
        interceptee_class = self.get_interceptee_class(obj)
        if interceptee_class is not None:
            return interceptee_class.objects.filter(interception_record__station=obj, person__role='PVOT',
                                                    interception_record__date_time_entered_into_system__year=datetime.date.today().year).count()
        else:
            return 0

    def get_country_name(self, obj):
        return obj.operating_country.name or "No Country"
    
    def get_country_currency(self, obj):
        return obj.operating_country.currency or ""
    
    def get_project_category_name(self, obj):
        if obj.project_category is not None:
            return obj.project_category.name
        else:
            return None


class InterceptionRecordListSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterceptionRecord
        fields = [
            'view_url',
            'edit_url',
            'delete_url',
            'id',
            'irf_number',
            'staff_name',
            'number_of_victims',
            'number_of_traffickers',
            'date_time_of_interception',
            'date_time_entered_into_system',
            'date_time_last_updated'
        ]

    view_url = serializers.HyperlinkedIdentityField(
        view_name='interceptionrecord_detail',
        read_only=True
    )
    edit_url = serializers.HyperlinkedIdentityField(
        view_name='interceptionrecord_update',
        read_only=True
    )
    delete_url = serializers.HyperlinkedIdentityField(
        view_name='InterceptionRecordDetail',
        read_only=True
    )


class InterceptionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = InterceptionRecord

    def validate(self, data):
        validation_response = {}
        errors = self.check_for_errors(data)
        warnings = self.check_for_warnings(data)
        if len(errors) > 0:
            validation_response['errors'] = errors
        if len(warnings) > 0:
            validation_response['warnings'] = warnings
        if len(warnings) > 0 or len(errors) > 0:
            raise serializers.ValidationError(validation_response)
        return data

    def check_for_errors(self, data):  # For Error validation
        errors = []
        errors += self.check_for_none_checked(data)
        if data['contact_noticed'] == False and data['staff_noticed'] == False:
            errors.append({'contact_noticed': 'Either Contact (6.0) or Staff (7.0) must be chosen for how interception was made.'})
        return errors

    def check_for_none_checked(self, data):  # For Error validation
        errors = []
        has_none_checked = True
        for field in data:
            if isinstance(data[field], bool) and data[field] == True:
                has_none_checked = False
        if has_none_checked:
            errors.append({'no_checkboxes_checked': 'At least one box must be checked on the first page.'})
        return errors

    def check_for_red_flags(self, data):  # For Warning validation
        warnings = []
        any_red_flags = False
        for field in InterceptionRecord._meta.fields:
            try:
                if field.weight is not None:
                    if data[field.name]:
                        any_red_flags = True
            except:
                pass
        if not any_red_flags:
            warnings.append({'red_flags': 'No red flags are checked.'})
        return warnings

    def check_for_warnings(self, data):  # For Warning validation
        warnings = []
        warnings += self.check_for_red_flags(data)
        warnings += self.check_procedure(data)
        warnings += self.check_type(data)
        if not data['has_signature']:
            warnings.append({'has_signature': 'Form should be signed, though not required.'})
        return warnings

    def check_procedure(self, data):  # For Warning validation
        warnings = []
        if not data['call_thn_to_cross_check']:
            warnings.append({'call_thn_to_cross_check': 'Procedure not followed.'})
        if not data['call_subcommittee_chair']:
            warnings.append({'call_subcommittee_chair': 'Procedure not followed.'})
        if not data['scan_and_submit_same_day']:
            warnings.append({'scan_and_submit_same_day': 'Procedure not followed.'})
        return warnings

    def check_type(self, data):  # For Warning validation
        warnings = []
        type_is_set = False
        for field in InterceptionRecord._meta.fields:
            try:
                if field.name:
                    if 'type' in field.name and data[field.name]:
                        type_is_set = True
            except:
                pass
        if not type_is_set:
            warnings.append({'interception_type': 'Field should be included, though not required.'})
        return warnings


class VictimInterviewListSerializer(serializers.ModelSerializer):
    class Meta:
        model = VictimInterview
        fields = [
            'view_url',
            'edit_url',
            'delete_url',
            'id',
            'vif_number',
            'interviewer',
            'number_of_victims',
            'number_of_traffickers',
            'date',
            'date_time_entered_into_system',
            'date_time_last_updated'
        ]

    view_url = serializers.HyperlinkedIdentityField(
        view_name='victiminterview_detail',
        read_only=True
    )
    edit_url = serializers.HyperlinkedIdentityField(
        view_name='victiminterview_update',
        read_only=True
    )
    delete_url = serializers.HyperlinkedIdentityField(
        view_name='VictimInterviewDetail',
        read_only=True
    )


class VictimInterviewPersonBoxSerializer(serializers.ModelSerializer):
    class Meta:
        model = VictimInterview
        exclude = []


class VictimInterviewLocationBoxSerializer(serializers.ModelSerializer):
    class Meta:
        model = VictimInterview
        exclude = []

class AddressTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddressType
        fields = '__all__'

class PhoneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneType
        fields = '__all__'
                
class SocialMediaTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneType
        fields = '__all__'

class PersonIdentificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonIdentification
        fields = '__all__'

class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = [
            'id',
            'full_name',
            'gender',
            'age',
            'address1',
            'address2',
            'address',
            'latitude',
            'longitude',
            'address_notes',
            'address_verified',
            'address_type',
            'phone_contact',
            'phone_verified',
            'phone_type',
            'birthdate',
            'estimated_birthdate',
            'nationality',
            'photo',
            'case_filed_against',
            'arrested',
            'social_media',
            'social_media_type',
            'role',
            'appearance',
            'occupation',
            'interviewer_believes',
            'pv_believes',
            'form_id',
            'form_type',
            'form_number',
            'station_id',
            'master_person_id',
            'master_set_by',
            'master_set_date',
            'master_set_notes',
            'personidentification_set',
        ]
        
    form_number = serializers.CharField(source='get_form_number', read_only=True)
    form_type = serializers.CharField(source='get_form_type', read_only=True)
    station_id = serializers.CharField(source='get_station_id', read_only=True)
    form_id = serializers.CharField(source='get_form_id', read_only=True)
    master_set_by = serializers.SerializerMethodField(read_only=True)
    personidentification_set = PersonIdentificationSerializer(many=True)
    master_person_id = serializers.SerializerMethodField(read_only=True)
        
    def get_master_set_by(self, obj):
        if obj.master_set_by is not None:
            return obj.master_set_by.get_full_name()
        else:
            return None
        
    def get_master_person_id(self, obj):
        if obj.master_person is not None:
            return obj.master_person.id
        else:
            return None

class PersonInMasterSerializer(PersonSerializer):
    class Meta:
        model = Person
        fields = [
            'id',
            'full_name',
            'gender',
            'age',
            'address1',
            'address2',
            'address',
            'latitude',
            'longitude',
            'address_notes',
            'address_verified',
            'address_type',
            'phone_contact',
            'phone_verified',
            'phone_type',
            'birthdate',
            'estimated_birthdate',
            'nationality',
            'photo',
            'case_filed_against',
            'arrested',
            'social_media',
            'social_media_verified',
            'social_media_type',
            'role',
            'appearance',
            'occupation',
            'interviewer_believes',
            'pv_believes',
            'form_id',
            'form_type',
            'form_number',
            'station_id',
            'master_set_by',
            'master_set_date',
            'master_set_notes',
            'personidentification_set',
        ]
        extra_kwargs = {
            'id':{'read_only': True},
            'full_name':{'read_only': True},
            'gender':{'read_only': True},
            'age':{'read_only': True},
            'address1':{'read_only': True},
            'address2':{'read_only': True},
            'address':{'read_only': True},
            'latitude':{'read_only': True},
            'longitude':{'read_only': True},
            'address_notes':{'read_only': True},
            'address_notes':{'read_only': True},
            'phone_contact':{'read_only': True},
            'birthdate':{'read_only': True},
            'estimated_birthdate':{'read_only': True},
            'nationality':{'read_only': True},
            'photo':{'read_only': True},
            'case_filed_against':{'read_only': True},
            'arrested':{'read_only': True},
            'social_media':{'read_only': True},
            'role':{'read_only': True},
            'appearance':{'read_only': True},
            'occupation':{'read_only': True},
            'interviewer_believes':{'read_only': True},
            'pv_believes':{'read_only': True},
            'form_id':{'read_only': True},
            'form_type':{'read_only': True},
            'form_number':{'read_only': True},
            'station_id':{'read_only': True},
            'master_set_by':{'read_only': True},
            'master_set_date':{'read_only': True},
            'master_set_notes':{'read_only': True},
            'personidentification_set':{'read_only': True},
        }
    
    def update(self, instance, validated_data):
        instance.address_verified = validated_data.get('address_verified', instance.address_verified)
        instance.address_type = validated_data.get('address_type', instance.address_type)
        instance.phone_verified = validated_data.get('phone_verified', instance.phone_verified)
        instance.phone_type = validated_data.get('phone_type', instance.phone_type)
        instance.social_media_verified = validated_data.get('social_media_verified', instance.social_media_verified)
        instance.social_media_type = validated_data.get('social_media_type', instance.social_media_type)
        instance.save()
        return instance

class PersonAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonAddress
        fields = '__all__'
        
class PersonPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonPhone
        fields = '__all__'

class PersonSocialMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonSocialMedia
        fields = '__all__'

class PersonDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonDocument
        fields = '__all__'
        
    def to_internal_value(self, data):
        ret = {}
        
        id = data.get('id')
        if id is not None:
            ret['id'] = id
        
        tmp = data.get('master_person_id')
        master_person = MasterPerson.objects.get(id=tmp)
        if master_person is not None:
            ret['master_person'] = master_person
        
        file_location = data.get('file_location')
        if file_location is not None:
            ret['file_location'] = 'person_documents/' + file_location
        
        tmp = data.get('document_type')
        document_type = DocumentType.objects.get(id=tmp)
        if document_type is not None:
            ret['document_type'] = document_type
        
        return ret
    
    def create(self, validated_data):
        obj = PersonDocument()
        obj.master_person = validated_data.get('master_person')
        obj.file_location = validated_data.get('file_location')
        obj.document_type = validated_data.get('document_type')
        obj.save()
        return obj
    
    def update(self, instance, validated_data):
        tmp = validated_data.get('file_location', instance.file_location)
        if tmp is not None:
            parts = tmp.split('/')
            tmp = 'person_documents/' + parts[len(parts)-1]

        instance.file_location = tmp
        instance.document_type = validated_data.get('document_type', instance.document_type)
        instance.save()
        return instance

class MasterPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterPerson
        fields = [
            'id',
            'full_name',
            'gender',
            'birthdate',
            'estimated_birthdate',
            'nationality',
            'appearance',
            'notes',
            'personaddress_set',
            'personphone_set',
            'personsocialmedia_set',
            'persondocument_set',
            'person_set',
        ]
    
    personaddress_set = PersonAddressSerializer(many=True, read_only=True)
    personphone_set = PersonPhoneSerializer(many=True, read_only=True)
    personsocialmedia_set = PersonSocialMediaSerializer(many=True, read_only=True)
    persondocument_set = PersonDocumentSerializer(many=True, read_only=True)
    person_set = PersonInMasterSerializer(many=True, read_only=True)

class PersonFormSerializer(serializers.ModelSerializer):
    form_id = serializers.CharField(source='get_form_id', read_only=True)
    form_type = serializers.CharField(source='get_form_type', read_only=True)
    form_name = serializers.CharField(source='get_form_name', read_only=True)
    form_number = serializers.CharField(source='get_form_number', read_only=True)
    form_date = serializers.CharField(source='get_form_date', read_only=True)
    station_id = serializers.CharField(source='get_station_id', read_only=True)
    country_id = serializers.CharField(source='get_country_id', read_only=True)
    country_name = serializers.CharField(source='get_country_name', read_only=True)
    
    
    class Meta:
        model = PersonForm
        fields = [
            'form_id',
            'form_type',
            'form_name',
            'form_number',
            'form_date',
            'station_id',
            'country_id',
            'country_name'
        ]

class IDManagementSerializer(serializers.ModelSerializer):
    aliases = serializers.CharField(source='get_aliases', read_only=True)
    address1 = Address1Serializer(read_only=True)
    address2 = Address2Serializer(read_only=True)
    alias_group = serializers.CharField(source='get_master_person_id', read_only=True)
    master_person = serializers.CharField(source='get_master_person_id', read_only=True)
    form = PersonFormSerializer(source="get_form", read_only=True)

    class Meta:
        model = Person
        fields = [
            'id',
            'full_name',
            'gender',
            'age',
            'address',
            'address1',
            'address2',
            'phone_contact',
            'role',
            'photo',
            'alias_group',
            'master_person',
            'aliases',
            'form'
        ]

class PersonFormsSerializer(serializers.Serializer):
    number = serializers.CharField()
    date = serializers.CharField()
    form_name = serializers.CharField()
    station_id = serializers.CharField()
    country_id= serializers.CharField()
    form_id= serializers.CharField()
    country_name = serializers.CharField()

class VictimInterviewSerializer(serializers.ModelSerializer):
    victim_guardian_address1 = Address1Serializer(read_only=True)
    victim_guardian_address2 = Address2Serializer(read_only=True)
    victim = PersonSerializer(read_only=True)

    class Meta:
        model = VictimInterview
        read_only_fields = ('person_boxes', 'location_boxes')
        exclude = []
        depth = 1


class IntercepteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interceptee
        fields = [
            'id',
            'interception_record',
            'relation_to',
            'person',
        ]
    person = PersonSerializer()
    

class InterceptionAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterceptionAlert
        fields = ['json']

    def to_representation(self, obj):
        alert_response = json.loads(obj.json)
        alert_response['id'] = obj.id
        alert_response['datetimeOfAlert'] = str(obj.created)
        return alert_response

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'permission_group', 'action', 'min_level', 'display_order',
                  'action_display_name', 'hide_action', 'group_display_name', 'hide_group']
    
    hide_action = serializers.SerializerMethodField(read_only=True)
    group_display_name = serializers.SerializerMethodField(read_only=True)
    hide_group = serializers.SerializerMethodField(read_only=True)
    
    def get_hide_action(self, obj):
        if obj.display_order == -1 and obj.hide_action:
            return True
        return False
    
    def get_group_display_name(self, obj):
        display_name = ''
        try:
            group = PermissionGroup.objects.get(permission_group=obj.permission_group)
            display_name = group.group_display_name
        except:
           display_name = obj.permission_group
        return display_name
    
    def get_hide_group(self, obj):
        try:
            group = PermissionGroup.objects.get(permission_group=obj.permission_group)
            hide_group = group.hide_display
        except:
           hide_group = False
           
        return hide_group
        
class UserLocationPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLocationPermission
        fields = ['id', 'account', 'country', 'station', 'permission']
        
    def create_local(self):
        perm = UserLocationPermission()
        perm.account = self.validated_data.get('account')
        perm.country = self.validated_data.get('country')  
        perm.station = self.validated_data.get('station')           
        perm.permission = self.validated_data.get('permission')
        
        return perm

class UserLocationPermissionEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    level = serializers.CharField()

class UserLocationPermissionListSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    name = serializers.CharField()
    permissions = UserLocationPermissionEntrySerializer(many=True)
    
class FormTypeSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = FormType 
        
class FormSerializer(serializers.ModelSerializer):
    form_type = FormTypeSerializer()
    
    class Meta:
        fields = ['id', 'form_name', 'form_type']
        model = Form

class StationStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationStatistics
        fields = [
            'id',
            'year_month',
            'compliance',
            'budget',
            'intercepts',
            'arrests',
            'gospel',
            'empowerment',
            'convictions',
            'station',
            'staff',
            'work_days',
            'is_station_open_now'
        ]
    
    intercepts = serializers.SerializerMethodField(read_only=True)
    arrests = serializers.SerializerMethodField(read_only=True)
    staff = serializers.SerializerMethodField(read_only=True)
    is_station_open_now = serializers.SerializerMethodField(read_only=True)
    
    def get_intercepts(self, obj):
        return LocationStatistics.objects.filter(location__border_station=obj.station, year_month=obj.year_month).aggregate(Sum('intercepts'))['intercepts__sum']
    
    def get_arrests(self, obj):
        return LocationStatistics.objects.filter(location__border_station=obj.station, year_month=obj.year_month).aggregate(Sum('arrests'))['arrests__sum']
    
    def get_staff(self, obj):
        work_days = StationStatistics.objects.get(station=obj.station, year_month=obj.year_month).work_days
        if work_days is None:
            work_days = 21
        total_days = LocationStaff.objects.filter(location__border_station=obj.station, year_month=obj.year_month).aggregate(Sum('work_fraction'))['work_fraction__sum']
        if total_days is None or work_days == 0:
            staff = None
        else:
            staff = total_days / work_days
        return staff

    def get_is_station_open_now(self, obj: StationStatistics):
        station = obj.station
        return station.open

    

class LocationStaffSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = LocationStaff

class LocationStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        fields = [
            'id',
            'year_month',
            'location',
            'staff',
            'intercepts',
            'arrests',
            ]
        model = LocationStatistics
    
    staff = serializers.SerializerMethodField(read_only=True)

    def get_staff(self, obj):
        work_days = StationStatistics.objects.get(station=obj.location.border_station, year_month=obj.year_month).work_days
        if work_days is None:
            work_days = 21
        total_days = LocationStaff.objects.filter(location=obj.location, year_month=obj.year_month).aggregate(Sum('work_fraction'))['work_fraction__sum']
        if total_days is None or work_days == 0:
            staff = None
        else:
            staff = total_days / work_days
        return staff
    
class CountryExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = CountryExchange

class PersonMatchSerializer(serializers.ModelSerializer):
    class Meta:
        fields = [
            'match_id',
            'master1_id',
            'master1_name',
            'master1_age',
            'master1_address',
            'master2_id',
            'master2_name',
            'master2_age',
            'master2_address',
            'match',
            'match_date',
            'matched_by',
            'notes',
            'match_results',
            ]
        model = PendingMatch
    
    match_id = serializers.SerializerMethodField(read_only=True)
    master1_id = serializers.SerializerMethodField(read_only=True)
    master1_name = serializers.SerializerMethodField(read_only=True)
    master1_age = serializers.SerializerMethodField(read_only=True)
    master1_address = serializers.SerializerMethodField(read_only=True)
    master2_id = serializers.SerializerMethodField(read_only=True)
    master2_name = serializers.SerializerMethodField(read_only=True)
    master2_age = serializers.SerializerMethodField(read_only=True)
    master2_address = serializers.SerializerMethodField(read_only=True)
    match = serializers.SerializerMethodField(read_only=True)
    match_date = serializers.SerializerMethodField(read_only=True)
    matched_by = serializers.SerializerMethodField(read_only=True)
    notes = serializers.SerializerMethodField(read_only=True)
    match_results = serializers.SerializerMethodField(read_only=True)
    
    def get_match_id(self, obj):
        return obj.person_match.id
    def get_master1_id(self, obj):
        return obj.person_match.master1.id
    def get_master1_name(self, obj):
        return obj.person_match.master1.full_name
    def get_master1_age(self, obj):
        return obj.person_match.master1.age
    def get_master1_address(self, obj):
        address = ''
        persons = Person.objects.filter(master_person=obj.person_match.master1)
        for person in persons:
             if person.address is not None and 'address' in person.address:
                address = person.address['address']
                break
        return address
    def get_master2_id(self, obj):
        return obj.person_match.master2.id
    def get_master2_name(self, obj):
        return obj.person_match.master2.full_name
    def get_master2_age(self, obj):
        return obj.person_match.master2.age
    def get_master2_address(self, obj):
        address = ''
        persons = Person.objects.filter(master_person=obj.person_match.master2)
        for person in persons:
            if person.address is not None and 'address' in person.address:
                address = person.address['address']
                break
        return address
    def get_match(self, obj):
        return obj.person_match.match_type.name
    def get_match_date(self, obj):
        return obj.person_match.match_date
    def get_matched_by(self, obj):
        name = ''
        if obj.person_match.matched_by is not None:
            name = obj.person_match.matched_by.get_full_name()
        return name
    def get_notes(self, obj):
        return obj.person_match.notes
    def get_match_results(self, obj):
        return obj.person_match.match_results

class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audit
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['form', 'form_type_name', 'country_name', 'total_samples', 'samples_complete', 'total_incorrect', 'samples_passed', 'author_name']
        
    form = serializers.SerializerMethodField(read_only=True)
    form_type_name = serializers.SerializerMethodField(read_only=True)
    country_name = serializers.SerializerMethodField(read_only=True)
    total_samples = serializers.SerializerMethodField(read_only=True)
    samples_complete = serializers.SerializerMethodField(read_only=True)
    total_incorrect = serializers.SerializerMethodField(read_only=True)
    samples_passed = serializers.SerializerMethodField(read_only=True)
    author_name = serializers.SerializerMethodField(read_only=True)
    
    def get_form_by_name(self, obj):
        form = Form.objects.get(form_name=obj.form_name)
        return form
    
    def get_form(self, obj):
        return self.get_form_by_name(obj).id
    
    def get_form_type_name(self, obj):
        return self.get_form_by_name(obj).form_type.name;
    
    def get_country_name(self, obj):
        return obj.country.name
    
    def get_total_samples(self, obj):
        return AuditSample.objects.filter(audit=obj).count();
    
    def get_samples_complete(self, obj):
        return AuditSample.objects.filter(audit=obj).exclude(completion_date__isnull=True).count()
    
    def get_total_incorrect(self, obj):
        completed = AuditSample.objects.filter(audit=obj).exclude(completion_date__isnull=True)
        total_incorrect = 0
        for sample in completed:
            for value in sample.results.values():
                if value is not None:
                    total_incorrect += value
        return total_incorrect
    
    def get_author_name(self, obj):
        if obj.author is None:
            return None
        else:
            return obj.author.get_full_name()
    
    def get_samples_passed (self, obj):
        total_questions = 0
        for section in obj.template:
            if section['questions'] is not None:
                total_questions += section['questions']
                
        completed = AuditSample.objects.filter(audit=obj).exclude(completion_date__isnull=True)
        passed = 0
        for sample in completed:
            total_incorrect = 0
            for value in sample.results.values():
                if value is not None:
                    total_incorrect += value
            
            if not sample.no_paper_form and total_questions > 0 and (total_questions - total_incorrect)/total_questions >= 0.95:
                passed += 1
        return passed
    
class AuditSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditSample
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['auditor_name', 'form_type', 'form_name', 'country_id', 'station_id']
        
    auditor_name = serializers.SerializerMethodField(read_only=True)
    form_type = serializers.SerializerMethodField(read_only=True)
    form_name = serializers.SerializerMethodField(read_only=True)
    country_id = serializers.SerializerMethodField(read_only=True)
    station_id = serializers.SerializerMethodField(read_only=True)
    
    def get_auditor_name(self, obj):
        if obj.auditor is None:
            return None
        else:
            return obj.auditor.get_full_name()
    
    def get_form_type(self, obj):
        form = Form.objects.get(form_name=obj.audit.form_name)
        return form.form_type.name

    def get_form_name(self, obj):
        return obj.audit.form_name
    
    def get_country_id(self, obj):
        return obj.audit.country_id
    
    def get_station_id(self, obj):
        form = Form.objects.get(form_name=obj.audit.form_name)
        storage_class = form.storage.get_form_storage_class()
        try:
            form_instance = storage_class.objects.get(id=obj.form_id)
            return form_instance.station.id
        except ObjectDoesNotExist:
            return None
    
class LegalCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalCase
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['form_name','country_id','station_code','number_victims','number_suspects','number_arrests']
    
    form_name = serializers.SerializerMethodField(read_only=True)
    country_id = serializers.SerializerMethodField(read_only=True)
    station_code = serializers.SerializerMethodField(read_only=True)
    number_victims = serializers.SerializerMethodField(read_only=True)
    number_suspects = serializers.SerializerMethodField(read_only=True)
    number_arrests = serializers.SerializerMethodField(read_only=True)
    
    def get_form_name(self, obj):
        forms = Form.objects.filter(form_type__name='LEGAL_CASE', stations__id=obj.station.id)
        if len(forms) > 0:
            return forms[0].form_name
        else:
            return None
    
    def get_country_id(self, obj):
        return obj.station.operating_country.id
    
    def get_station_code(self, obj):
        return obj.station.station_code
    
    def get_number_victims(self, obj):
        return LegalCaseVictim.objects.filter(legal_case=obj).count()
    
    def get_number_suspects(self, obj):
        return LegalCaseSuspect.objects.filter(legal_case=obj).count()
    
    def get_number_arrests(self, obj):
        return LegalCaseSuspect.objects.filter(legal_case=obj, arrest_status__startswith="Yes").count()
    
class GospelVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GospelVerification
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['vdf_number','pv_name','vdf_date', 'form_name', 'country', 'profess_to_accept_christ']   
        
    vdf_number = serializers.SerializerMethodField(read_only=True)
    pv_name = serializers.SerializerMethodField(read_only=True)
    vdf_date = serializers.SerializerMethodField(read_only=True)
    form_name = serializers.SerializerMethodField(read_only=True)
    country = serializers.SerializerMethodField(read_only=True)
    profess_to_accept_christ = serializers.SerializerMethodField(read_only=True)
    
    def get_vdf_number(self, obj):
        return obj.vdf.vdf_number
    def get_pv_name(self, obj):
        return obj.vdf.victim.full_name
    def get_vdf_date(self, obj):
        return obj.vdf.interview_date
    def get_country(self, obj):
        return obj.station.operating_country.id
    def get_form_name(self, obj):
        forms = Form.objects.filter(form_type__name='GOSPEL_VERIFICATION', stations__id=obj.station.id)
        if len(forms) > 0:
            return forms[0].form_name
        else:
            return None
    def get_profess_to_accept_christ(self, obj):
        if obj.date_of_followup is not None:
            if obj.vdf.what_victim_believes_now == 'Came to believe that Jesus is the one true God':
                return 'Yes'
            else:
                return 'No'
        
        return ''

class ClientDiagnosticSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ClientDiagnostic

class ProjectCategorySerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ProjectCategory

class EmpowermentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empowerment
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['levels', 'station_name', 'country_name', 'country_id']
    
    station_name = serializers.SerializerMethodField(read_only=True)
    country_name = serializers.SerializerMethodField(read_only=True)
    country_id = serializers.SerializerMethodField(read_only=True)
    
    def get_station_name (self, obj):
        if obj.station is not None:
            return obj.station.station_name
        else:
            return None
    
    def get_country_name (self, obj):
        if obj.station is not None and obj.station.operating_country is not None:
            return obj.station.operating_country.name
        else:
            return None
    
    def get_country_id (self, obj):
        if obj.station is not None and obj.station.operating_country is not None:
            return obj.station.operating_country.id
        else:
            return None

class GospelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gospel
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['station_name', 'country_name', 'country_id']
    
    station_name = serializers.SerializerMethodField(read_only=True)
    country_name = serializers.SerializerMethodField(read_only=True)
    country_id = serializers.SerializerMethodField(read_only=True)
    
    def get_station_name (self, obj):
        if obj.station is not None:
            return obj.station.station_name;
        else:
            return None
    
    def get_country_name (self, obj):
        if obj.station is not None and obj.station.operating_country is not None:
            return obj.station.operating_country.name;
        else:
            return None
        
    def get_country_id (self, obj):
        if obj.station is not None and obj.station.operating_country is not None:
            return obj.station.operating_country.id;
        else:
            return None

class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['station_name', 'country_id']
    
    station_name = serializers.SerializerMethodField(read_only=True)
    country_id = serializers.SerializerMethodField(read_only=True)
    
    def get_station_name (self, obj):
        if obj.station is not None:
            return obj.station.station_name;
        else:
            return None
        
    def get_country_id (self, obj):
        if obj.station is not None:
            return obj.station.operating_country.id;
        else:
            return None
    
    def get_country_id (self, obj):
        if obj.station is not None:
            return obj.station.operating_country.id;
        else:
            return None
    
    def create(self, validated_data):
        #incident_number comes in with just the station code.  Add date and sequence number
        date_match = self.context['request'].data['incident_number'] + self.context['request'].data['incident_date'].replace('-','') + "_"
        matches = Incident.objects.filter(incident_number__startswith=date_match).order_by('-incident_number')
        if len(matches) < 1:
            validated_data['incident_number'] = date_match + '01'
        else:
            parts = matches[0].incident_number.split('_')
            new_sequence = str(int(parts[1]) + 1)
            if len(new_sequence) < 2:
                new_sequence = '0' + new_sequence
            validated_data['incident_number'] = date_match + str(new_sequence)
        
        return Incident.objects.create(**validated_data)
    