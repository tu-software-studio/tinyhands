from django.db import models

from .form import BaseCard
from .country import Country

class ProjectCategory(models.Model):
    name = models.CharField(max_length=127)
    sort_order = models.PositiveIntegerField(default=999)

def get_border_station_default_category():
        project_categories =  ProjectCategory.objects.filter(name='Transit Stations')
        if len(project_categories) < 1:
            return None
        else:
            return project_categories[0].id
    
class BorderStation(models.Model):
    station_code = models.CharField(max_length=3, unique=True)
    station_name = models.CharField(max_length=100)
    date_established = models.DateField(null=True)
    has_shelter = models.BooleanField(default=False)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    open = models.BooleanField(default=True)
    operating_country = models.ForeignKey(Country, models.SET_NULL, null=True, blank=True)
    time_zone = models.CharField(max_length=127, blank=False)
    auto_number= models.CharField(max_length=127, null=True)
    project_category = models.ForeignKey(ProjectCategory, models.SET_NULL, null=True, default=get_border_station_default_category)
    features = models.CharField(max_length=512, default='hasStaff;hasSubcommittee;hasProjectStats;hasLocations;hasLocationStaffing;hasForms')
    mdf_project = models.ForeignKey('self', null=True, on_delete=models.CASCADE)
    
    def get_country_id(self):
        if self.operating_country is None:
            return None
        return self.operating_country.id
    
    
    def get_border_station_id(self):
        return self.id
    
    def get_key(self):
        return self.station_code
    
    def pre_save(self, form_data):
        pass
    
    def post_save(self, form_data):
        pass

    def __str__(self):
        return self.station_name


class BorderStationAttachment(BaseCard):
    project = models.ForeignKey(BorderStation, on_delete=models.CASCADE)
    attachment_number = models.PositiveIntegerField(null=True, blank=True)
    attachment = models.FileField('Attach scanned forms related to projects', upload_to='project_attachments')
    option = models.CharField(max_length=126, null=True)

    def set_parent(self, the_parent):
        self.project = the_parent
