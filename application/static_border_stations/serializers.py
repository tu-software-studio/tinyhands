import datetime
from decimal import Decimal
from rest_framework import serializers
from django.conf import settings
from budget.models import ProjectRequest
import budget.mdf_constants as constants
from dataentry.models import BorderStation, CountryExchange, UserLocationPermission
from static_border_stations.models import Staff, StaffAttachment, StaffProject, StaffReview, CommitteeMember, Location, StaffMiscellaneous, StaffMiscellaneousTypes, WorksOnProject
from budget.models import MonthlyDistributionForm, ProjectRequest, StaffBudgetItem
import budget.mdf_constants as constants

class StaffProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffProject
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['project_code', 'project_name', 'country_id', 'project_category']
        
    project_code = serializers.SerializerMethodField(read_only=True)
    project_name = serializers.SerializerMethodField(read_only=True)
    country_id = serializers.SerializerMethodField(read_only=True)
    project_category = serializers.SerializerMethodField(read_only=True)
    
    def get_project_code (self, obj):
        return obj.border_station.station_code

    def get_project_name (self, obj):
        return obj.border_station.station_name
    
    def get_country_id (self, obj):
        return obj.border_station.operating_country.id
    
    def get_project_category (self, obj):
        if obj.border_station.project_category is None:
            return None
        else:
            return obj.border_station.project_category.name

class StaffReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffReview
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['total']
    
    total = serializers.SerializerMethodField(read_only=True)
    
    def get_total(self, obj):
        result = '';
        total = 0;
        for fld in ['networking', 'compliance', 'dependability', 'alertness', 'boldness', 'questioning', 'teamwork']:
            value = getattr(obj, fld, None)
            if value is not None:
                total += value
        
        if total != 0:
            result = total
        
        return result;

class BaseStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'position',
                  'receives_money_distribution_form', 'border_station', 'country', 'country_name',
                  'first_date', 'last_date', 'birth_date', 'photo', 'total_years', 'gender',
                  'education', 'id_card_expiration', 'staffproject_set', 'miscellaneous',
                  'contract_data', 'knowledge_data', 'review_data', 'has_pbs']
    
    total_years = serializers.SerializerMethodField(read_only=True)
    #staffproject_set = StaffProjectSerializer(many=True)
    contract_data = serializers.SerializerMethodField(read_only=True)
    knowledge_data = serializers.SerializerMethodField(read_only=True)
    review_data = serializers.SerializerMethodField(read_only=True)
    miscellaneous = serializers.SerializerMethodField(read_only=True)
    has_pbs = serializers.SerializerMethodField(read_only=True)
    country_name = serializers.SerializerMethodField(read_only=True)
    
    def view_section(self, obj, data_type):
        result = False
        if 'user_permissions' in self.context and 'request' in self.context:
            user_permissions = self.context['user_permissions']
            request = self.context['request']
        else:
            user_permissions = None
        if user_permissions is not None:
            request_types = request.GET.get('include')
            if request_types is None:
                request_types = ''
            if request_types is not None and data_type in request_types:
                if UserLocationPermission.has_permission_in_list(user_permissions, 'STAFF', data_type,
                                obj.country.id,
                                None):
                    result = True
                else:
                    for staff_project in obj.get_staff_benefits_projects():
                        if UserLocationPermission.has_permission_in_list(user_permissions, 'STAFF', data_type,
                                    staff_project.operating_country.id,
                                    staff_project.id):
                            result = True
                        else:
                            # if they do not have permissions for one project, then they are not allowed to view
                            result = False
                            break
            
        return result
    
    def get_total_years(self, obj):
        if obj.first_date is not None:
            delta = datetime.datetime.today().date() - obj.first_date
            years = delta.days/356
        else:
            years = None
        return years
    
    def get_contract_data(self, obj):
        if  not self.view_section(obj, 'VIEW_CONTRACT'):
            return None
        
        contract = False
        contract_expiration = None
        agreement = False
        attachments = StaffAttachment.objects.filter(staff=obj).order_by('-attach_date')
        for attachment in attachments:
            if contract is False and attachment.option == 'Contract':
                contract = True
                contract_expiration = attachment.expiration_date
            if agreement is False and attachment.option == 'C & M':
                agreement = True
        
        result = {
                "agreement":agreement,
                "contract":contract,
                "contract_expiration":contract_expiration,
                "last_month":{"local":obj.last_month_local, "USD": obj.last_month_usd},
                "twelve_month":{"local":obj.twelve_month_local, "USD": obj.twelve_month_usd}
            }
        return result
    
    def get_knowledge_data(self, obj):
        result = {
            "general":obj.general,
            "awareness":obj.awareness,
            "security":obj.security,
            "accounting":obj.accounting,
            "pv_care":obj.pv_care,
            "paralegal":obj.paralegal,
            "records":obj.records,
            "shelter":obj.shelter
            }
        return result
    
    def get_review_data(self, obj):
        if  not self.view_section(obj, 'VIEW_REVIEW'):
            return None
        result = {
            "review_count":0
            }
        reviews = StaffReview.objects.filter(staff=obj).order_by('-review_date')
        if len(reviews) > 0 :
            reviewSerializer=StaffReviewSerializer(reviews[0])
            result = reviewSerializer.data
            result["review_count"] = len(reviews)
            
        return result
    
    def get_miscellaneous(self, obj):
        if 'request' not in self.context or self.context['request'].GET.get('include') != 'miscellaneous':
            return []
        
        misc_items = []
        misc_types = StaffMiscellaneousTypes.objects.filter(countries=obj.country).order_by('name')
        for misc_type in misc_types:
            try:
                item = StaffMiscellaneous.objects.get(staff=obj, type=misc_type)
            except:
                item = StaffMiscellaneous()
                item.staff = obj
                item.type = misc_type
            misc_items.append(item)
        
        serializer = StaffMiscellaneousSerializer(misc_items, many=True)
        return serializer.data
    
    def get_has_pbs(self, obj):
        return MonthlyDistributionForm.objects.filter(border_station__operating_country = obj.country).exists()

    def get_country_name(self, obj):
        if obj.country:
            return obj.country.name
        else:
            return None
    
    def to_internal_value(self, data):
        if 'country' in data and data['country'] is not None:
            data['country_id'] = data['country']
        if 'staffproject_set' in data:
            staff_project = data['staffproject_set']
            data['staffproject_set'] = []
        else:
            data['staffproject_set'] = []
            staff_project = []
        validated = super().to_internal_value(data)
        validated['staffproject_set'] = staff_project
        return validated
    
    def update(self, instance, validated_data):
        staff_project = validated_data['staffproject_set']
        del validated_data['staffproject_set']
        obj = super().update(instance, validated_data)
        to_delete = []
        staff_project_list = StaffProject.objects.filter(staff=obj)
        for existing in staff_project_list:
            found = False
            for new_data in staff_project:
                if existing.id == new_data['id']:
                    found = True
                    existing.receives_money_distribution_form = new_data['receives_money_distribution_form']
                    existing.coordinator = new_data['coordinator']
                    existing.save()
                    break
            if not found:
                to_delete.append(existing)

        for existing in to_delete:
            existing.delete()

        for new_data in staff_project:
            if new_data['id'] is None:
                entry = StaffProject()
                entry.staff = instance
                entry.border_station = BorderStation.objects.get(id=new_data['border_station'])
                entry.receives_money_distribution_form = new_data['receives_money_distribution_form']
                entry.coordinator = new_data['coordinator']
                entry.save()
        
        return obj

    def create(self, validated_data):
        staff_project = validated_data['staffproject_set']
        del validated_data['staffproject_set']
        obj = super().create(validated_data)
        obj.save()
        for new_data in staff_project:
            entry = StaffProject()
            entry.staff = obj
            entry.border_station = BorderStation.objects.get(id=new_data['border_station'])
            entry.receives_money_distribution_form = new_data['receives_money_distribution_form']
            entry.coordinator = new_data['coordinator']
            entry.save()
        
        return obj

class StaffSerializer(BaseStaffSerializer):
    staffproject_set = StaffProjectSerializer(many=True)
    
class BlankStaffSerializer(BaseStaffSerializer):
    staffproject_set = serializers.SerializerMethodField(read_only=True)
    
    def get_staffproject_set(self, obj):
        return []


class MiniBorderStationSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id','station_code','station_name', 'operating_country']
        model = BorderStation

class StaffKnowledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = ['id', 'general', 'awareness', 'security', 'accounting',
                  'pv_care', 'paralegal', 'records', 'shelter']

class StaffMiscellaneousTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffMiscellaneousTypes
        fields = [field.name for field in model._meta.fields] # all the model fields

class StaffMiscellaneousSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffMiscellaneous
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['type_detail']
        
    type_detail = serializers.SerializerMethodField(read_only=True)
    
    def get_type_detail(self, obj):
       serializer = StaffMiscellaneousTypesSerializer(obj.type)
       return serializer.data

class StaffAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffAttachment
        fields = [field.name for field in model._meta.fields] # all the model fields
    
class CommitteeMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommitteeMember
        fields = [field.name for field in model._meta.fields] # all the model fields
        fields = fields + ['member_projects', 'project_text', 'country_name']
       
    
    sc_agreement = serializers.SerializerMethodField(read_only=True)
    misconduct_agreement = serializers.SerializerMethodField(read_only=True)
    member_projects = serializers.SerializerMethodField()
    project_text = serializers.SerializerMethodField(read_only=True)
    country_name = serializers.SerializerMethodField(read_only=True)
    
    def can_view_contract(self, obj):
        result = False
        if 'user_permissions' in self.context and 'request' in self.context:
            user_permissions = self.context['user_permissions']
            request = self.context['request']
        else:
            user_permissions = None
        if user_permissions is not None:
            if obj.country is not None and UserLocationPermission.has_permission_in_list(user_permissions,
                    'SUBCOMMITTEE', 'VIEW_CONTRACT', obj.country.id,  None):
                result = True
            
        return result
    
    def get_sc_agreement(self, obj):
        result = None
        if obj.sc_agreement is not None and obj.sc_agreement != '' and self.can_view_contract(obj):
            result=serializers.ImageField(use_url=True).to_representation(obj.sc_agreement)
            if 'request' in self.context:
                result = self.context['request'].build_absolute_uri(result)
 
        return result
    
    def get_misconduct_agreement(self, obj):
        result = None
        if obj.misconduct_agreement is not None and obj.misconduct_agreement != '' and self.can_view_contract(obj):
            result =serializers.ImageField().to_representation(obj.misconduct_agreement)
            if 'request' in self.context:
                result = self.context['request'].build_absolute_uri(result)
        
        return result
    
    def get_member_projects(self, obj):
        result = []
        if obj.id is not None:
            for member in obj.member_projects.all().order_by('station_name'):
                result.append(member.id)
        return result
    
    def get_project_text(self, obj):
        result = ''
        if obj.id is not None:
            sep = ''
            for member in obj.member_projects.all().order_by('station_name'):
                result += sep + member.station_name
                sep = '/'
        return result

    def get_country_name(self, obj):
        if obj.country:
            return obj.country.name
        else:
            return None
    
    def to_internal_value(self, data):
        if 'member_projects' in data:
            member_projects = data['member_projects']
            data['member_projects'] = []
        else:
            data['member_projects'] = []
            member_projects = []
        validated = super().to_internal_value(data)
        validated['member_projects'] = member_projects
        return validated
    
    def update(self, instance, validated_data):
        member_projects = validated_data['member_projects']
        del validated_data['member_projects']
        obj = super().update(instance, validated_data)

        obj.member_projects.clear()
        for project_id in member_projects:
            border_station = BorderStation.objects.get(id=project_id)
            obj.member_projects.add(border_station)
        obj.save()
        
        return obj

    def create(self, validated_data):
        member_projects = validated_data['member_projects']
        del validated_data['member_projects']
        obj = super().create(validated_data)
        for project_id in member_projects:
            border_station = BorderStation.objects.get(id=project_id)
            obj.member_projects.add(border_station)
        obj.save()
        
        return obj

    
class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Location
