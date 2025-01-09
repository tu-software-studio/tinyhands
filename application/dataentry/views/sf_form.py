import pytz
import datetime

from rest_framework import status
from rest_framework import serializers
from rest_framework import filters as fs
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from templated_email import send_templated_mail

from dataentry.serialize_form import FormDataSerializer
from .base_form import BaseFormViewSet, BorderStationOverviewSerializer
from dataentry.serializers import IncidentSerializer

from dataentry.form_data import Form, FormData
from dataentry.models import Person, UserLocationPermission, Incident, Suspect

class SfListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sf_number = serializers.SerializerMethodField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True)
    gender = serializers.SerializerMethodField(read_only=True)
    age = serializers.SerializerMethodField(read_only=True)
    station = BorderStationOverviewSerializer()
    form_name = serializers.SerializerMethodField(read_only=True)
    incident = serializers.SerializerMethodField(read_only=True)
    
    
    perm_group_name = 'SF'
    
    def get_sf_number(self, obj):
        return obj.sf_number
    
    def get_name(self, obj):
        if obj.merged_person is not None:
            return obj.merged_person.full_name
        else:
            return ''
    
    def get_gender(self, obj):
        if obj.merged_person is not None:
             return obj.merged_person.gender
        else:
             return ''
       
    def get_age(self, obj):
        age = None
        estimated = False
        if obj.merged_person is not None:
            birthdate = obj.merged_person.birthdate
            if birthdate is None:
                birthdate = obj.merged_person.estimated_birthdate
                estimated = True
            if birthdate is not None:
                current = datetime.datetime.now()
                age = current.year - birthdate.year
                if current.timetuple().tm_yday < birthdate.timetuple().tm_yday:
                    age -= 1
                if estimated:
                    age = str(age) + '(est)'
                
        return age
    
    def get_form_name(self, obj):
        forms = Form.objects.filter(form_type__name='SF', stations__id=obj.station.id)
        if len(forms) > 0:
            return forms[0].form_name
        else:
            return None
    
    def get_incident(self, obj):
        
        incident_number = obj.sf_number
        for idx in range(3,len(obj.sf_number)):
            if obj.sf_number[idx] != '_' and (obj.sf_number[idx] < '0' or obj.sf_number[idx] > '9'):
                incident_number = obj.sf_number[0:idx]
                break
        try:
            incident = Incident.objects.get(incident_number=incident_number)
            return incident.id
        except ObjectDoesNotExist:
            return None
    
class SfFormViewSet(BaseFormViewSet):
    parser_classes = (MultiPartParser,FormParser,JSONParser)
    permission_classes = (IsAuthenticated, )
    serializer_class = SfListSerializer
    filter_backends = (fs.SearchFilter, fs.OrderingFilter,)
    search_fields = ('sf_number', 'merged_person__full_name', 'merged_person__gender')
    ordering_fields = [
        'id', 'sf_number', 'merged_person__full_name', 'merged_person__gender']
    ordering = ('-sf_number')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SfListSerializer
        else:
            return FormDataSerializer
    
    def get_serializer_context(self): 
        return self.serializer_context
    
    def get_perm_group_name(self):
        return 'SF'
    
    def get_form_type_name(self):
        return 'SF'
    
    def get_element_paths(self):
        return [
            {
                'element':'scanned',
                'path':'sf_attachments/'
            }]
    
    def get_list_field_names(self):
        return ['id']
        
    def get_empty_queryset(self):
        return Suspect.objects.none()
    
    def filter_key(self, queryset, search):
        return queryset.filter(sf_number__contains=search)
    
    def post_create(self, form_data):
        sf_number = form_data.form_object.sf_number
        incident_number = ''
        for idx in range(len(sf_number)-1,2,-1):
            if sf_number[idx] >= '0' and sf_number[idx] <= '9':
                incident_number = sf_number[0:idx+1]
                break
        
        incident = Incident.objects.get(incident_number=incident_number)
        form_data.form_object.incidents.add(incident)
    
    def custom_create_blank(self, form_object):
        form_object.merged_person = Person()
        
    def has_common_master_person(self):
        return True
    
    def get_common_master_person(self, form):
        return form.get_common_master_person()
    
    def get_associated_incidents(self, request, pk):
        sf = Suspect.objects.get(id=pk)
        associated_incidents = sf.associated_incidents.all();
        serializer = IncidentSerializer(associated_incidents, many=True, context={'request': request})
        return Response(serializer.data)
    
    def set_associated_incidents(self, request, pk):
        sf = Suspect.objects.get(id=pk)
        add_incident = []
        for incident_id in request.data:
            incident = Incident.objects.get(id=incident_id)
            add_incident.append(incident)
        
        sf.associated_incidents.clear()
        
        for incident in add_incident:
            sf.associated_incidents.add(incident)
        
        return Response('')
                

   
    



