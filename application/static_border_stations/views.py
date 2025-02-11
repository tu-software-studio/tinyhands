import json
import pytz
import time
import csv
import io
from datetime import date

from PIL import Image
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from django.db.models import Q
from django_filters import rest_framework as filters
from django.core.files.storage import default_storage
from django.http import HttpResponse
from rest_framework import filters as fs
from dateutil import parser

from dataentry.models import BorderStation, Country, CountryExchange, UserLocationPermission
from dataentry.serializers import BorderStationSerializer
from rest_api.authentication_expansion import HasPermission, HasDeletePermission, HasPostPermission, HasPutPermission, RequestPermission
from static_border_stations.models import Staff, CommitteeMember, Location, StaffProject, WorksOnProject, StaffReview, StaffMiscellaneous, StaffMiscellaneousTypes, StaffAttachment
from static_border_stations.serializers import BlankStaffSerializer, StaffSerializer, StaffKnowledgeSerializer, StaffReviewSerializer, StaffAttachmentSerializer, CommitteeMemberSerializer, LocationSerializer
from static_border_stations.serializers import StaffMiscellaneousSerializer, StaffMiscellaneousTypesSerializer
from budget.models import ProjectRequest, StaffBudgetItem
import budget.mdf_constants as constants


class BorderStationViewSet(viewsets.ModelViewSet):
    queryset = BorderStation.objects.all()
    serializer_class = BorderStationSerializer
    permission_classes = (IsAuthenticated, HasPermission, HasPostPermission, HasPutPermission)
    permissions_required = [{'permission_group':'PROJECTS', 'action':'VIEW'},]
    post_permissions_required = [{'permission_group':'PROJECTS', 'action':'ADD'},]
    put_permissions_required = [{'permission_group':'PROJECTS', 'action':'EDIT'},]
    filter_backends = (fs.SearchFilter, fs.OrderingFilter,)
    ordering_fields = (
        'station_name', 'station_code', 'operating_country__name', 'project_category__name', )
    ordering = ('station_name',)
    search_fields = ('station_name', 'station_code',)
    
    @action(detail=False)
    def list_all(self, request):
        border_stations = BorderStation.objects.all().order_by('station_name')
        country_param = request.query_params.get('operating_country', None)
        if country_param is not None:
            border_stations = border_stations.filter(operating_country=country_param)
        open_param = request.query_params.get('open', None)
        if open_param in ['True', 'true']:
            border_stations = border_stations.filter(open=True)
        elif open_param in ['False', 'false']:
            border_stations = border_stations.filter(open=False)
        serializer = self.get_serializer(border_stations, many=True)
        return Response(serializer.data)
    
    def get_queryset(self):
        border_stations = UserLocationPermission.get_stations_with_permission(self.request.user.id, 'PROJECTS','VIEW')
        border_station_ids = []
        for border_station in border_stations:
            border_station_ids.append(border_station.id)
        queryset = BorderStation.objects.filter(id__in=border_station_ids)
        in_country = self.request.GET.get('country_ids')
        if in_country is not None and in_country != '':
            queryset = queryset.filter(operating_country__id__in=in_country.split(','))

        project_category = self.request.GET.get('project_category')
        if project_category is not None and project_category != '':
            queryset = queryset.filter(project_category__name=project_category)

        include_closed = self.request.GET.get('include_closed')
        if include_closed is not None and include_closed != 'true':
            queryset = queryset.filter(open=True)


        return queryset


@api_view(['GET'])
@permission_classes((IsAuthenticated, ))
def get_station_id(request):
    code = request.GET['code']
    if code == '':
        return Response(-1)
    else:
        station = BorderStation.objects.filter(station_code=code)
        if len(station) > 0:
            return Response(station[0].id)
        else:
            return Response(-1)


class BorderStationRestAPI(viewsets.ModelViewSet):
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('border_station',)
    permission_classes = (IsAuthenticated, HasPermission, HasPostPermission, HasPutPermission)
    permissions_required = [{'permission_group':'PROJECTS', 'action':'VIEW'},]
    post_permissions_required = [{'permission_group':'PROJECTS', 'action':'ADD'},]
    put_permissions_required = [{'permission_group':'PROJECTS', 'action':'EDIT'},]


class LocationViewSet(BorderStationRestAPI):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    ordering = ('name',)
    
    def retrieve_border_station_locations(self, request, *args, **kwargs):
        """
            retrieve all locations for a particular border_station
        """
        station = BorderStation.objects.get(id=self.kwargs['pk'])
        Location.get_or_create_other_location(station)
        Location.get_or_create_leave_location(station)
        self.object_list = self.filter_queryset(self.get_queryset().filter(border_station=station))
        if request.GET.get('include_inactive') is None:
            self.object_list = self.object_list.filter(active=True)
        if request.GET.get('location_type') is not None:
            self.object_list = self.object_list.filter(location_type=request.GET.get('location_type'))
        self.object_list = self.object_list.order_by('-active', 'name')
        serializer = self.get_serializer(self.object_list, many=True)
        return Response(serializer.data)


class CommitteeMemberViewSet(viewsets.ModelViewSet):
    queryset = CommitteeMember.objects.all()
    serializer_class = CommitteeMemberSerializer
    permission_classes = (IsAuthenticated, HasPermission, HasPostPermission, HasPutPermission)
    permissions_required = [{'permission_group':'SUBCOMMITTEE', 'action':'VIEW_BASIC'},]
    post_permissions_required = [{'permission_group':'SUBCOMMITTEE', 'action':'ADD'},]  
    put_permissions_required = [{'permission_group':'SUBCOMMITTEE', 'action':'EDIT_BASIC'},]
    filter_backends = (fs.SearchFilter, fs.OrderingFilter,) 
    ordering_fields = ('first_name', 'last_name', )
    ordering = ('first_name',)
    search_fields = ('first_name', 'last_name', 'phone',)
    
    def get_queryset(self):
        countries = UserLocationPermission.get_countries_with_permission(self.request.user.id, 'SUBCOMMITTEE','VIEW_BASIC')
        
        queryset = self.queryset.filter(country__in=countries)
        in_country = self.request.GET.get('country_ids')
        if in_country is not None and in_country != '':
            queryset = queryset.filter(country__id__in=in_country.split(','))
        
        in_project = self.request.GET.get('project_id')
        if in_project is not None and in_project != '':
            queryset = queryset.filter(member_projects__id=in_project)

        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        if ('request' in context):
            user_permissions = UserLocationPermission.objects.filter(account=context['request'].user, permission__permission_group='SUBCOMMITTEE')
            context['user_permissions'] = user_permissions
        return context
    
    def retrieve_blank(self, request):
        committee_member = CommitteeMember()
                
        serializer = CommitteeMemberSerializer(committee_member)
        return Response(serializer.data)
    
    def save_file(self, file_obj, subdirectory):
        with default_storage.open(subdirectory + file_obj.name, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        
        return  subdirectory + file_obj.name
    
    def create(self, request):
        request_string = request.data['member']
        request_json = json.loads(request_string)
        if 'sc_agreement' in request.data:
            file_obj = request.data['sc_agreement']
            sc_agreement_file = self.save_file(file_obj, 'committee/sc_agreement/')
        else:
            sc_agreement_file = None
        
        if 'misconduct_agreement' in request.data:
            file_obj = request.data['misconduct_agreement']
            misconduct_agreement_file = self.save_file(file_obj, 'committee/misconduct/')
        else:
             misconduct_agreement_file = None
        
        serializer = self.get_serializer(data=request_json)
        serializer.is_valid(raise_exception=True)
        committee_member = serializer.save()
        if committee_member.country is not None and UserLocationPermission.has_session_permission(request, 'SUBCOMMITTEE', 'EDIT_CONTRACT', committee_member.country.id, None):
            if sc_agreement_file:
                committee_member.sc_agreement.name = sc_agreement_file
            if misconduct_agreement_file:
                committee_member.misconduct_agreement.name = misconduct_agreement_file
            committee_member.save()
        
        self.get_serializer_context()
        serializer_new =  self.get_serializer(committee_member)
        return Response(serializer_new.data)       
    
    def update(self, request, pk):
        request_string = request.data['member']
        request_json = json.loads(request_string)
        committee_member = CommitteeMember.objects.get(id=pk)
        if 'sc_agreement_file' in request.data:
            file_obj = request.data['sc_agreement_file']
            sc_agreement_file = self.save_file(file_obj, 'committee/sc_agreement/')
        else:
            sc_agreement_file = None
        
        if 'misconduct_agreement_file' in request.data:
            file_obj = request.data['misconduct_agreement_file']
            misconduct_agreement_file = self.save_file(file_obj, 'committee/misconduct/')
        else:
             misconduct_agreement_file = None
        
        serializer = self.get_serializer(committee_member, data=request_json)
        serializer.is_valid(raise_exception=True)
        committee_member = serializer.save()
        if UserLocationPermission.has_session_permission(request, 'SUBCOMMITTEE', 'EDIT_CONTRACT', committee_member.country.id, None):
            if sc_agreement_file:
                committee_member.sc_agreement.name = sc_agreement_file
            if misconduct_agreement_file:
                committee_member.misconduct_agreement.name = misconduct_agreement_file
            committee_member.save()
        serializer_new =  self.get_serializer(committee_member)
        return Response(serializer_new.data) 

# Custom permission handling for Staff because it does not have a single Project/BorderStation
class StaffRequestPermission(RequestPermission):
    def custom_has_object_permission(self, request, view, method, permissions_required, obj):
        found = True
        if request.method == method or method == "ANY":
            # Need to have a way to access the country id and border station id from the object
            # Assume each model will implement property get methods for country_id and border_station_id
            get_country_id = getattr(obj, 'get_country_id', None)
            if get_country_id is not None and callable(get_country_id):
                country_id = obj.get_country_id()
            else:
                country_id = None
            
            staff_projects = obj.get_staff_projects()
            
            found = True
            # Staff has permission if they have all the required permissions for the whole country
            for permission in permissions_required:
                if not UserLocationPermission.has_session_permission(request, permission['permission_group'], permission['action'], country_id, None):
                    # country missing at least one required permission
                    found = False
                    break
            if not found:
                # Staff has permission if they have all the required permissions for at least one station
                for staff_project in staff_projects:
                    station_id = staff_project.border_station.id
                    found = True
                    for permission in permissions_required:
                        if not UserLocationPermission.has_session_permission(request, permission['permission_group'], permission['action'], country_id, station_id):
                            self.message = self.message.format(permission)
                            # station is missing at least one required permission
                            found = False
                            break
                    if found:
                        break
        
        return found
    
class StaffHasPermission(StaffRequestPermission):
    def has_permission(self, request, view):
        return self.custom_has_permission(request, view, "ANY", view.permissions_required)
    
    def has_object_permission(self, request, view, obj):
        return self.custom_has_object_permission(request, view, "ANY", view.permissions_required, obj)


class StaffHasDeletePermission(StaffRequestPermission):
    def has_permission(self, request, view):
        return self.custom_has_permission(request, view, "DELETE", view.delete_permissions_required)
    
    def has_object_permission(self, request, view, obj):
        return self.custom_has_object_permission(request, view, "DELETE", view.delete_permissions_required, obj)
    
class StaffHasGetPermission(StaffRequestPermission):
    def has_permission(self, request, view):
        return self.custom_has_permission(request, view, "GET", view.get_permissions_required)
    
    def has_object_permission(self, request, view, obj):
        return self.custom_has_object_permission(request, view, "GET", view.get_permissions_required, obj)


class StaffHasPostPermission(StaffRequestPermission):
    def has_permission(self, request, view):
        return self.custom_has_permission(request, view, "POST", view.post_permissions_required)

    def has_object_permission(self, request, view, obj):
        return self.custom_has_object_permission(request, view, "POST", view.post_permissions_required, obj)

class StaffHasPutPermission(StaffRequestPermission):
    def has_permission(self, request, view):
        return self.custom_has_permission(request, view, "PUT", view.put_permissions_required)
    
    def has_object_permission(self, request, view, obj):
        return self.custom_has_object_permission(request, view, "PUT", view.put_permissions_required, obj)


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    permission_classes = (IsAuthenticated, StaffHasPermission, StaffHasDeletePermission, StaffHasPostPermission, StaffHasPutPermission)
    permissions_required = [{'permission_group':'STAFF', 'action':'VIEW_BASIC'},]
    delete_permissions_required = [{'permission_group':'STAFF', 'action':'DELETE'},]
    post_permissions_required = [{'permission_group':'STAFF', 'action':'ADD'},]  
    put_permissions_required = [{'permission_group':'STAFF', 'action':'EDIT_BASIC'},]
    filter_backends = (fs.SearchFilter, fs.OrderingFilter,) 
    search_fields = ('first_name', 'last_name',)
    ordering_fields = (
        'first_name', 'last_name', )
    ordering = ('first_name','last_name')
    
    def save_file(self, file_obj, subdirectory):
        with default_storage.open(subdirectory + file_obj.name, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        
        return  subdirectory + file_obj.name
    
    def create(self, request):
        request_string = request.data['staff']
        request_json = json.loads(request_string)
        
        photo_file = None
        if 'attachment_file' in request.data:
            file_obj = request.data['attachment_file']
            photo_file = self.save_file(file_obj, 'staff_photos/')
        
        del request_json['photo']
        serializer = StaffSerializer(data=request_json)
        serializer.is_valid(raise_exception=True)
        new_staff = serializer.save()
        if photo_file is not None:
            new_staff.photo.name = photo_file
            new_staff.save()
        if 'miscellaneous' in request_json and len(request_json['miscellaneous']) > 0:
            for entry in request_json['miscellaneous']:
                entry['staff'] = new_staff.id;
                if 'value' not in entry or entry['value'] is None:
                    entry['value'] = ''
                misc_serializer = StaffMiscellaneousSerializer(data=entry)
                if misc_serializer.is_valid():
                    misc_serializer.save()
                else:
                    return Response(misc_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer_new = StaffSerializer(new_staff, context={'request':request})
        return Response(serializer_new.data)
    
    def update(self, request, pk):
        request_string = request.data['staff']
        request_json = json.loads(request_string)
        staff = Staff.objects.get(id=pk)
        
        photo_file = None
        if 'attachment_file' in request.data:
            file_obj = request.data['attachment_file']
            photo_file = self.save_file(file_obj, 'staff_photos/')
        
        del request_json['photo']
        serializer = StaffSerializer(staff, data=request_json)
        serializer.is_valid(raise_exception=True)
        new_staff = serializer.save()
        if photo_file is not None:
            new_staff.photo.name = photo_file
            new_staff.save()

        if 'miscellaneous' in request_json and len(request_json['miscellaneous']) > 0:
            for entry in request_json['miscellaneous']:
                entry['staff'] = new_staff.id;
                if 'value' not in entry or entry['value'] is None:
                    entry['value'] = ''
                # Should be at most only one existing entry
                existing_entries = StaffMiscellaneous.objects.filter(staff=new_staff, type=entry['type'])
                if len(existing_entries) > 0:
                    old = existing_entries[0]
                    misc_serializer = StaffMiscellaneousSerializer(old, data=entry)
                else:
                    misc_serializer = StaffMiscellaneousSerializer(data=entry)
                if misc_serializer.is_valid():
                    misc_serializer.save()
                else:
                    return Response(misc_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer_new = StaffSerializer(new_staff, context={'request':request})
        return Response(serializer_new.data)
        
    
    def get_queryset(self):
        countries = UserLocationPermission.get_countries_with_permission(self.request.user.id, 'STAFF','VIEW_BASIC')
        stations = UserLocationPermission.get_stations_with_permission(self.request.user.id, 'STAFF','VIEW_BASIC')
        
        queryset = self.queryset.filter(Q(country__in=countries) | Q(staffproject__border_station__in=stations), last_date__isnull=True).distinct()
        in_country = self.request.GET.get('country_ids')
        if in_country is not None and in_country != '':
            queryset = queryset.filter(country__id__in=in_country.split(','))

        project_id = self.request.GET.get('project_id')
        if project_id is not None and project_id != '':
            queryset = queryset.filter(staffproject__border_station__id=project_id)

        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        if ('request' in context):
            user_permissions = UserLocationPermission.objects.filter(account=context['request'].user, permission__permission_group='STAFF')
            context['user_permissions'] = user_permissions
        return context

    def retrieve_border_station_staff(self, request, *args, **kwargs):
        """
            retrieve all the staff for a particular border_station
        """
        self.object_list = self.get_queryset().filter(staffproject__border_station__id=self.kwargs['pk'])
        if request.GET.get('include_inactive') is None:
            self.object_list = self.object_list.filter(last_date__isnull=True)
        serializer = self.get_serializer(self.object_list, many=True)
        return Response(serializer.data)
    
    def getStaff(self, include_inactive, include_financial):
        staff = []
        
        works_on_list = WorksOnProject.objects.filter(border_station__id=self.kwargs['pk'])
        for works_on in works_on_list:
            if works_on.staff not in staff and (include_inactive or works_on.staff.last_date is None):
                staff.append(works_on.staff)
        if include_financial:
            financial_list = self.filter_queryset(self.get_queryset().filter(border_station=self.kwargs['pk']))
            for financial in financial_list:
                if financial not in staff and (include_inactive or financial.last_date is None):
                    staff.append(financial)
        
        return staff
    
    def retrieve_blank(self, request):
        staff = Staff()

        serializer = BlankStaffSerializer(staff)
        return Response(serializer.data)
    
    def build_csv_headers(self, row):
        headers = []
        exclude = ['id','miscellaneous']
        for key in row.keys():
            if key in exclude:
                continue
            if key == 'contract_data':
                headers += ['contract', 'contract expiration','last month local','last month USD','twelve month local','twelve month usd']
            elif key == 'knowledge_data':
                headers += ['general','awareness','security','awareness','security']
            elif key == 'review_data':
                pass
            else:
                headers.append(key)
        
        return headers
            
    
    def retrieve_csv(self, request, pk):
        country = Country.objects.get(id=pk)
        export_name=country.name +'-staff.csv'
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        header_row = []
        
        staff_fields = []
        staff_exclude = ['id','border_station', 'country']
        for field in Staff._meta.get_fields():
            value = str(field)
            if 'ManyTo' in value or field.name in staff_exclude:
                continue
            staff_fields.append(field)
            header_row.append(field.name.replace('_',' '))
        
        header_row.append('projects')
        review_fields = []
        review_exclude = ['id', 'staff']
        for field in StaffReview._meta.get_fields():
            value = str(field)
            if field.name in review_exclude:
                continue
            review_fields.append(field)
            header_row.append(field.name.replace('_',' '))
        
        header_row.append('contract')
        header_row.append('contract expiration')
        header_row.append('C & M')
        writer.writerow(header_row)
        
        blank_review = StaffReview()
        staff_list = Staff.objects.filter(country__id=pk).exclude(last_date__isnull=False).order_by('first_name','last_name')
        for staff in staff_list:
            if staff.last_name == '__general_staff':
                continue
            row = []
            for field in staff_fields:
                row.append(getattr(staff, field.name, ''))
            
            staff_projects = StaffProject.objects.filter(staff=staff)
            projects = ''
            sep = ''
            for staff_project in staff_projects:
                projects += sep + staff_project.border_station.station_code
                sep = '/'
            row.append(projects)
            reviews = StaffReview.objects.filter(staff=staff).order_by('-review_date')
            if len(reviews) > 0:
                review = reviews[0]
            else:
                review = blank_review
            for field in review_fields:
                row.append(getattr(review, field.name, ''))
            
            contracts = StaffAttachment.objects.filter(staff=staff, option='Contract').order_by('-expiration_date')
            if len(contracts) > 0:
                row.append(True)
                row.append(contracts[0].expiration_date)
            else:
                row.append(False)
                row.append('')
            c_and_m =  StaffAttachment.objects.filter(staff=staff, option='C & M')
            if len(c_and_m) > 0:
                row.append(True)
            else:
                row.append(False)
            
            writer.writerow(row)
        csv_file.seek(0)
        response = HttpResponse(csv_file.read(), content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename=' + export_name
        return response
    
    def getValue(self, data, path):
        current = data
        for piece in path:
            if piece not in current:
                return None
            current = current[piece]
        
        return current
    
    def update_border_station_staff_work(self, request, pk):
        for staff in request.data:
            staff_id = self.getValue(staff, ['id'])
            works_on = self.getValue(staff, ['works_on'])
            if (staff_id is None or works_on is None):
                continue
            for work_element in works_on:
                financial_id = self.getValue(work_element, ['financial', 'project_id'])
                percent = self.getValue(work_element, ['percent'])
                work_id = self.getValue(work_element, ['works_on', 'project_id'])
                id = self.getValue(work_element, ['id'])
                if financial_id is None or percent is None or work_id is None:
                    continue
                if str(financial_id) != str(pk):
                    continue
                
                staff = Staff.objects.get(id=staff_id)
                border_station = BorderStation.objects.get(id=work_id)
                if id is None:
                    works_on_project = WorksOnProject()
                else:
                    works_on_project = WorksOnProject.objects.get(id=id)
                
                works_on_project.staff = staff
                works_on_project.work_percent = percent
                works_on_project.border_station = border_station
                works_on_project.save()
        
        staff = self.getStaff(False, True)
                    
        serializer = self.get_serializer(staff, many=True)
        return Response(serializer.data)
    
    def save_file(self, file_obj, subdirectory):
        with default_storage.open(subdirectory + file_obj.name, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        
        return  subdirectory + file_obj.name
    
    def put_contract(self, request, pk):
        request_string = request.data['contract']
        request_json = json.loads(request_string)
        staff = Staff.objects.get(id=pk)
        if 'contract_file' in request.data:
            file_obj = request.data['contract_file']
            contract_file = self.save_file(file_obj, 'staff/contract/')
        else:
            contract_file = None
        
        if 'agreement_file' in request.data:
            file_obj = request.data['agreement_file']
            agreement_file = self.save_file(file_obj, 'staff/agreement/')
        else:
             agreement_file = None
        
        if request_json['contract_expiration'] is not None and request_json['contract_expiration'] != '':
            staff.contract_expiration = parser.parse(request_json['contract_expiration']).date()
        if contract_file:
            staff.contract.name = contract_file
        if agreement_file:
            staff.agreement.name = agreement_file
        staff.save()
        
        user_permissions = UserLocationPermission.objects.filter(account=request.user, permission__permission_group='STAFF')
        serializer_new = StaffContractSerializer(staff, context={'request':request, 'user_permissions':user_permissions})
        return Response(serializer_new.data)
        
    
    def get_contract_project_requests(self, request, pk, year, month):
        result = {'exchange_rate':1, 'year':year, 'month':month, 'project_request':[]}
        staff = Staff.objects.get(id=pk)
        year_month = int(year)*100 + int(month)
        exchange = CountryExchange.objects.filter(country=staff.country, year_month__lte=year_month).order_by('-year_month')
        if len(exchange) > 0:
            result['exchange_rate'] = exchange[0].exchange_rate
        else:
            result['exchange_rate'] = 1.0
            
        projects = UserLocationPermission.get_stations_with_permission(self.request.user.id, 'STAFF','VIEW_CONTRACT')
        
        request_totals = {}
        
        queryset = ProjectRequest.objects.filter(staff=staff,
                                                project__in=projects,
                                                category=constants.STAFF_BENEFITS,
                                                monthlydistributionform__month_year__month = month,
                                                monthlydistributionform__month_year__year = year)
        for item in queryset:
            if item.benefit_type_name in request_totals:
                request_totals[item.benefit_type_name] += item.cost
            else:
                request_totals[item.benefit_type_name] = item.cost
        
        queryset = StaffBudgetItem.objects.filter(staff_person=staff,
                                                  work_project__in = projects,
                                                  cost__isnull=False,
                                                  budget_calc_sheet__month_year__month = month,
                                                  budget_calc_sheet__month_year__year = year)
        for item in queryset:
            type_name = item.type_name.replace('~','')
            if type_name in request_totals:
                request_totals[item.type_name] += item.cost
            else:
                request_totals[item.type_name] = item.cost
        
        for key in request_totals:
            result['project_request'].append({'benefit_type_name':key, 'cost':str(request_totals[key])})
                
        return Response(result)
        
    
    def retrieve_knowledge(self, request, pk):
        staff = Staff.objects.get(id=pk)
        serializer = StaffKnowledgeSerializer(staff)
        return Response(serializer.data)
    
    def put_knowledge(self, request, pk):
        staff = Staff.objects.get(id=pk)
        serializer = StaffKnowledgeSerializer(staff, request.data)
        serializer.is_valid(raise_exception=True)
        staff = serializer.save()
        serializer = StaffKnowledgeSerializer(staff)
        return Response(serializer.data)

class StaffMiscellaneousViewSet(viewsets.ModelViewSet):
    queryset = StaffMiscellaneous.objects.all()
    serializer_class = StaffMiscellaneousSerializer
    permission_classes = (IsAuthenticated, )
    filter_backends = (fs.OrderingFilter,) 
    ordering_fields = ('id', )
    ordering = ('id',)
        

class StaffReviewViewSet(viewsets.ModelViewSet):
    queryset = StaffReview.objects.all()
    serializer_class = StaffReviewSerializer
    permission_classes = (IsAuthenticated, )
    filter_backends = (fs.OrderingFilter,) 
    ordering_fields = ('id', )
    ordering = ('id',)
    
    def get_queryset(self):
        if (self.action == 'list'):
            staff_id = self.request.GET.get('staff_id')
            if staff_id is not None and staff_id != '':
                queryset = StaffReview.objects.filter(staff__id = staff_id)
        else:
            queryset = StaffReview.objects.all()

        return queryset
 
class StaffAttachmentViewSet(viewsets.ModelViewSet):
    queryset = StaffAttachment.objects.all()
    serializer_class = StaffAttachmentSerializer
    permission_classes = (IsAuthenticated, )
    filter_backends = (fs.OrderingFilter,) 
    ordering_fields = ('attach_date', )
    ordering = ('-attach_date',)
    
    def save_file(self, file_obj, subdirectory):
        with default_storage.open(subdirectory + file_obj.name, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        
        return  subdirectory + file_obj.name
    
    def get_queryset(self):
        stations = UserLocationPermission.get_stations_with_permission(self.request.user.id, 'STAFF','VIEW_CONTRACT')
        if (self.action == 'list'):
            staff_id = self.request.GET.get('staff_id')
            if staff_id is not None and staff_id != '':
                staff_projects = StaffProject.objects.filter(staff__id = staff_id, border_station__in=stations)
                if len(staff_projects) > 0:
                    queryset = StaffAttachment.objects.filter(staff__id = staff_id)
                else:
                    queryset = StaffAttachment.objects.none()
        else:
            queryset = StaffAttachment.objects.all()

        return queryset
    
    def create(self, request):
        request_string = request.data['attachment']
        request_json = json.loads(request_string)
        
        attachment_file = None
        if 'attachment_file' in request.data:
            file_obj = request.data['attachment_file']
            attachment_file = self.save_file(file_obj, 'staff_attachment/')
        else:
            contract_file = None
        
        del request_json['attachment']
        del request_json['attach_date'] 
        serializer = StaffAttachmentSerializer(data=request_json)
        serializer.is_valid(raise_exception=True)
        attachment = serializer.save()
        if attachment_file is not None:
            attachment.attachment.name = attachment_file
            attachment.save()
        serializer_new = StaffAttachmentSerializer(attachment)
        return Response(serializer_new.data)

    def update(self, request, pk):
        old_attachment = StaffAttachment.objects.get(id=pk)
        request_string = request.data['attachment']
        request_json = json.loads(request_string)
        attachment_file = None
        if 'attachment_file' in request.data:
            file_obj = request.data['attachment_file']
            attachment_file = self.save_file(file_obj, 'staff_attachment/')
        else:
            contract_file = None
        
        del request_json['attachment']
        if request_json['attach_date'] is None:
            del request_json['attach_date']
        
        serializer = StaffAttachmentSerializer(old_attachment, data=request_json)
        serializer.is_valid(raise_exception=True)
        attachment = serializer.save()
        if attachment_file is not None:
            attachment.attachment.name = attachment_file
            attachment.save()
        serializer_new = StaffAttachmentSerializer(attachment)
        return Response(serializer_new.data)

class TimeZoneViewSet(viewsets.ViewSet):
    def get_time_zones(self, request):
        return Response(pytz.all_timezones)
