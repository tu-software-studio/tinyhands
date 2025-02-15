import logging
import zipfile
from io import BytesIO
from datetime import datetime
from time import strptime, mktime
from typing import List

from braces.views import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.db.models import Q, QuerySet
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import View
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dataentry.models import BorderStation
from dataentry.models import Form
from dataentry.models import Interceptee
from dataentry.models import InterceptionRecord
from dataentry.models import Storage
from dataentry.models import UserLocationPermission
from rest_api.authentication import HasPermission
from accounts.mixins import PermissionsRequiredMixin


logger = logging.getLogger(__name__)


class PhotoExporter(viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated, HasPermission)
    permissions_required = ['permission_irf_view']

    def get_photos_old(self, start, end):
        return Interceptee.objects.filter(interception_record__date_time_of_interception__gte=start,
                                          interception_record__date_time_of_interception__lte=end).exclude(photo="").values_list('photo', 'person__full_name', 'interception_record__irf_number')
    
    def add_q_filter(self, base_filter, addition):
        if base_filter is None:
            return addition
        else:
            return (base_filter | addition)
                                    
    def build_q_for_perms(self, irf_view_perms):
        q_filter = None
        for perm in irf_view_perms:
            if perm.country is None and perm.station is None:
                q_filter = None
                break
            if perm.country is None:
                q_filter = self.add_q_filter(q_filter, Q(interception_record__station=perm.station))
            else:
                q_filter = self.add_q_filter(q_filter, Q(interception_record__station__operating_country=perm.country))
        
        return q_filter          
    
    def get_photos(self, request, start_date, end_date) -> QuerySet:
        start = timezone.make_aware(datetime.fromtimestamp(mktime(strptime(start_date, '%m-%d-%Y'))), timezone.get_default_timezone())
        end = timezone.make_aware(datetime.fromtimestamp(mktime(strptime(end_date, '%m-%d-%Y'))), timezone.get_default_timezone())
        
        all_stations = False
        stations_with_perms = []
        irf_view_perms = UserLocationPermission.objects.filter(account=request.user, permission__permission_group='IRF',
                                                               permission__action='VIEW PI')
        for perm in irf_view_perms:
            if perm.country is None and perm.station is None:
                all_stations = True
                break
            if perm.country is None:
                if perm.station not in stations_with_perms:
                    stations_with_perms.append(perm.station)
            else:
                if perm.country not in stations_with_perms:
                    stations = BorderStation.objects.filter(operating_country=perm.country)
                    for station in stations:
                        stations_with_perms.append(station)
            
        forms = Form.objects.filter(form_type__name = 'IRF')
        if not all_stations:
            forms = forms.filter(stations__in=stations_with_perms)
        
        parent_storage_list = []
        for form in forms:
            if form.storage not in parent_storage_list:
                parent_storage_list.append(form.storage)
            
        station_filter = self.build_q_for_perms(irf_view_perms)
        interceptee_storage_qs = Storage.objects.filter(foreign_key_field_parent='interception_record',
                                                     parent_storage__in=parent_storage_list)
        photos_qs = None
        for storage in interceptee_storage_qs:
            mod = __import__(storage.module_name, fromlist=[storage.form_model_name])
            card_model = getattr(mod, storage.form_model_name, None)
            try:
                card_model._meta.get_field('person')
            except:
                # Not an interceptee model
                continue
            tmp_qs = card_model.objects.filter(interception_record__verified_date__gte=start,
                                          interception_record__verified_date__lte=end,
                                          interception_record__status='verified').exclude(person__photo="")
            if station_filter is not None:
                tmp_qs = tmp_qs.filter(station_filter)
                
            if photos_qs is None:
                photos_qs = tmp_qs.values_list('person__photo', 'person__full_name', 'interception_record__irf_number')
            else:
                photos_qs = photos_qs.union(tmp_qs.values_list('person__photo', 'person__full_name', 'interception_record__irf_number'))
        
        if photos_qs is None:
            photos_qs = Interceptee.objects.none()
            
        return photos_qs

    def count_photos_in_date_range(self, request, start_date, end_date):
            return Response({"count": self.get_photos(request, start_date, end_date).count()})

    def export_photos(self, request, start_date, end_date):
        photos: List = list(self.get_photos(request, start_date, end_date))
        if len(photos) == 0:
            return Response({'detail' : "No photos found in specified date range"}, status = status.HTTP_400_BAD_REQUEST)

        for i in range(len(photos)):
            photos[i] = [str(x) for x in photos[i]]

        f = BytesIO()
        imagezip = zipfile.ZipFile(f, 'w')
        for photoTuple in photos:
            irf_number = photoTuple[1]
            try:
                photo_url = photoTuple[0]
                with default_storage.open(photo_url) as image_file:
                    person_name = photoTuple[2]
                    imagezip.writestr(str(person_name) + '-' + str(irf_number) + '.jpg', image_file.read())
            except:
                logger.error('Could not find photo: ' + irf_number + '.jpg')
        imagezip.close()

        response = HttpResponse(f.getvalue(), content_type="application/zip")
        response['Content-Disposition'] = 'attachment; filename=irfPhotos ' + start_date + ' to ' + end_date + '.zip'
        return response
