import pytz

from rest_framework import serializers
from rest_framework import filters as fs
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from dataentry.serialize_form import FormDataSerializer
from .base_form import BaseFormViewSet, BorderStationOverviewSerializer

from dataentry.form_data import Form, FormData
from dataentry.models import BorderStation, ProjectCategory
from dataentry.serializers import ProjectCategorySerializer


    
class BorderStationFormViewSet(BaseFormViewSet):
    parser_classes = (MultiPartParser,FormParser,JSONParser)
    permission_classes = (IsAuthenticated, )
    
    def get_serializer_class(self):
        return FormDataSerializer
    
    def get_serializer_context(self): 
        return self.serializer_context

    def get_perm_group_name(self):
        return 'PROJECTS'
    
    def get_form_type_name(self):
        return 'BORDER_STATION'

    def get_element_paths(self):
        return [
            {
                'element': 'scanned',
                'path': 'project_attachments/'
            }
        ]
    
    def get_list_field_names(self):
        return []
        
    def get_empty_queryset(self):
        return BorderStation.objects.none()
    
    def filter_key(self, queryset, search):
        return queryset
    
    def retrieve_blank(self, request):
        return self.retrieve_blank_form(request, None)
    
    def retrieve(self, request, pk):
        return self.my_retrieve(request, None, pk)
    
    def update(self, request, pk):
        return super().update(request, None, pk)
    
    def get_project_categories(self, request):
        qs = ProjectCategory.objects.all().order_by('sort_order')
        serializer = ProjectCategorySerializer(qs, many=True, context={'request': request})
        return Response(serializer.data) 

