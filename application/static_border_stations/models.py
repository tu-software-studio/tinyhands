from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db import models
from django.apps import apps
from dataentry.models import BorderStation, Country
from django.core.exceptions import ObjectDoesNotExist
import budget.mdf_constants as constants


class NullableEmailField(models.EmailField):
    description = "EmailField that stores NULL but returns ''"

    def from_db_value(self, value, expression, connection):
        if value is None:
            return ''
        return value

    def to_python(self, value):
        if isinstance(value, models.EmailField):
            return value
        return value or ''

    def get_prep_value(self, value):
        return value or None


class Person(models.Model):
    email = NullableEmailField(blank=True, null=True, default=None, unique=False)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=2048, blank=True, null=True)
    receives_money_distribution_form = models.BooleanField(default=False)
    border_station = models.ForeignKey(BorderStation, null=True, on_delete=models.CASCADE)
    country = models.ForeignKey('dataentry.Country', null=True, on_delete=models.CASCADE)
    

    class Meta:
        abstract = True

    @property
    def full_name(self):
        return self.first_name + ' ' + self.last_name
    
    def get_country_id(self):
        if self.border_station is None or self.border_station.operating_country is None:
            return None
        return self.border_station.operating_country.id
    
    def get_border_station_id(self):
        if self.border_station is None:
            return None
        return self.border_station.id

    def __str__(self):
        return self.full_name
    
    def set_parent(self, the_parent):
        self.border_station = the_parent
    
    def is_private(self):
        return False

class Staff(Person):
    class Meta:
        abstract = False
        
    first_date = models.DateField(default=date.today)
    last_date = models.DateField(null=True)
    
    #start new fields
    birth_date = models.CharField(max_length=127, blank=True)
    education = models.CharField(max_length=127, null=True)
    id_card_expiration = models.DateField(null=True)
    photo = models.ImageField(upload_to='staff_photos', default='', blank=True)
    gender = models.CharField(max_length=127, null=True)
    
    #contract
    last_month_local = models.DecimalField(max_digits=17, decimal_places=2, default=0, blank=False)
    last_month_usd = models.DecimalField(max_digits=17, decimal_places=2, default=0, blank=False)
    twelve_month_local = models.DecimalField(max_digits=17, decimal_places=2, default=0, blank=False)
    twelve_month_usd = models.DecimalField(max_digits=17, decimal_places=2, default=0, blank=False)
    
    #knowledge
    general = models.DateField(null=True)
    awareness = models.DateField(null=True)
    security = models.DateField(null=True)
    accounting = models.DateField(null=True)
    pv_care = models.DateField(null=True)
    paralegal = models.DateField(null=True)
    records = models.DateField(null=True)
    shelter = models.DateField(null=True)
    
    
    general_staff = '__general_staff'
    
    def get_staff_projects(self):
        return self.staffproject_set.all()
    
    def get_country_id(self):
        if self.country:
            return self.country.id
        return None

    def get_staff_benefits_projects(self):
        results = []
        for staff_project in self.staffproject_set.all():
            results.append(staff_project.border_station)
            
        project_request_class = apps.get_model('budget', 'ProjectRequest')
        project_requests = project_request_class.objects.filter(staff=self, category=constants.STAFF_BENEFITS)
        for project_request in project_requests:
            if project_request.project not in results:
                results.append(project_request.project)
                
        staff_item_class = apps.get_model('budget', 'StaffBudgetItem')
        staff_items = staff_item_class.objects.filter(staff_person=self)
        for staff_item in staff_items:
            if staff_item.work_project not in results:
                results.append(staff_item.work_project)
        
        return results
    
    @staticmethod
    def set_all_totals():
        countries = Country.objects.all()
        for country in countries:
            the_staff = Staff.objects.filter(country=country, last_date__isnull=True)
            Staff.set_totals(the_staff, country)
    
    @staticmethod
    def set_mdf_totals(mdf):
        the_staff = []
        project_requests = mdf.requests.filter(category=constants.STAFF_BENEFITS, staff__isnull=False)
        for project_request in project_requests:
            if project_request.staff not in the_staff:
                the_staff.append(project_request.staff)
        Staff.set_totals(the_staff, the_staff[0].country)
    
    @staticmethod
    def set_totals(the_staff, country):
        current_time = datetime.today()
        end_time = current_time.replace(day=1, hour=0, minute=0,second=0, microsecond=0)
        start_time = end_time.replace(year=end_time.year - 1)
        last_month_time = end_time - timedelta(days=1)
        
        # build exchange rate dictionary
        exchange_rates = {}
        exchange_rate_class = apps.get_model('dataentry','CountryExchange')
        month = last_month_time.month
        year = last_month_time.year
        for index in range(0,12):
            exchange_rate_entries = exchange_rate_class.objects.filter(country=country, year_month__lte=year*100+month).order_by('-year_month')
            if len(exchange_rate_entries) > 0:
                exchange_rates[year*100+month] = Decimal(exchange_rate_entries[0].exchange_rate)
            else:
                exchange_rates[year*100+month] = Decimal(1.0)
            
            month -= 1
            if month < 1:
                month = 12
                year -= 1
        
        for staff in the_staff:
            staff.last_month_local = 0
            staff.last_month_usd = 0
            staff.twelve_month_local = 0
            staff.twelve_month_usd = 0
            
            Staff.total_requests(staff, start_time, end_time, exchange_rates, last_month_time.month)
            Staff.total_budget_items(staff, start_time, end_time, exchange_rates, last_month_time.month)
            staff.save()
    
    @staticmethod
    def total_requests(staff, start_time, end_time, exchange_rates, last_month):
        project_request_class = apps.get_model('budget', 'ProjectRequest')
        project_requests = project_request_class.objects.filter(staff=staff,
                                                                category=constants.STAFF_BENEFITS,
                                                                monthlydistributionform__month_year__gte=start_time,
                                                                monthlydistributionform__month_year__lt=end_time,
                                                                monthlydistributionform__status = 'Approved').distinct()
        for project_request in project_requests:
            # request can be on multiple MDFs
            mdfs = project_request.monthlydistributionform_set.filter(month_year__gte=start_time,
                                                                month_year__lt=end_time,
                                                                status = 'Approved')
            cost = project_request.cost
            if project_request.benefit_type_name == 'Deductions':
                cost = -cost
            for mdf in mdfs:
                year_month = mdf.month_year.year * 100 + mdf.month_year.month
                staff.twelve_month_local += cost
                staff.twelve_month_usd += cost / exchange_rates[year_month]
                if mdf.month_year.month == last_month:
                    staff.last_month_local += cost
                    staff.last_month_usd += cost / exchange_rates[year_month]
    
    @staticmethod
    def total_budget_items(staff, start_time, end_time, exchange_rates, last_month):
        staff_item_class = apps.get_model('budget', 'StaffBudgetItem')
        staff_items = staff_item_class.objects.filter(staff_person=staff,
                                                      budget_calc_sheet__month_year__gte=start_time,
                                                      budget_calc_sheet__month_year__lt=end_time,
                                                      cost__isnull=False)
        for staff_item in staff_items:
            cost = staff_item.cost
            if staff_item.type_name == 'Deductions':
                cost = -cost
            year_month = staff_item.budget_calc_sheet.month_year.year * 100 + staff_item.budget_calc_sheet.month_year.month
            staff.twelve_month_local += cost
            staff.twelve_month_usd += cost /exchange_rates[year_month]
            if staff_item.budget_calc_sheet.month_year.month == last_month:
                staff.last_month_local += cost
                staff.last_month_usd += cost / exchange_rates[year_month]
        
    
    @staticmethod 
    def get_or_create_general_staff(border_station):
        try:
            general = Staff.objects.get(border_station=border_station, last_name=Staff.general_staff)
        except ObjectDoesNotExist:
            general = Staff()
            general.last_name = Staff.general_staff
            general.border_station = border_station
            general.first_date = date.today()
            general.last_date = general.first_date
            general.save()
        
        return general

class StaffReview(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    review_date = models.DateField()
    networking = models.FloatField(null=True)
    compliance = models.FloatField(null=True)
    dependability = models.FloatField(null=True)
    alertness = models.FloatField(null=True)
    boldness = models.FloatField(null=True)
    questioning = models.FloatField(null=True)
    teamwork = models.FloatField(null=True)
    
    def get_country_id(self):
        return staff.get_country_id()
    
    def get_staff_projects(self):
        return staff.get_staff_projects()

class StaffMiscellaneousTypes(models.Model):
    name = models.CharField(max_length=127)
    countries = models.ManyToManyField(Country)
    type = models.CharField(max_length=127)
    choices = models.TextField(blank=True)
    
    def get_country_id(self):
        return staff.get_country_id()
    
    def get_staff_projects(self):
        return staff.get_staff_projects()

class StaffMiscellaneous(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    type = models.ForeignKey(StaffMiscellaneousTypes, on_delete=models.CASCADE)
    value = models.CharField(max_length=127, blank=True)
    
    def get_country_id(self):
        return staff.get_country_id()
    
    def get_staff_projects(self):
        return staff.get_staff_projects()

class CommitteeMember(Person):
    class Meta:
        abstract = False
    
    member_projects = models.ManyToManyField(BorderStation, related_name='member_projects')
    sc_agreement = models.ImageField(upload_to='committee/sc_agreement', default='', blank=True)
    misconduct_agreement = models.ImageField(upload_to='committee/misconduct', default='', blank=True)

class Location(models.Model):
    name = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    border_station = models.ForeignKey(BorderStation, null=True, on_delete=models.CASCADE)
    location_type = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    
    other_name = '__Other'
    leave_name = 'Leave'
    
    def get_country_id(self):
        if self.border_station is None or self.border_station.operating_country is None:
            return None
        return self.border_station.operating_country.id
    
    def get_border_station_id(self):
        if self.border_station is None:
            return None
        return self.border_station.id
    
    def set_parent(self, the_parent):
        self.border_station = the_parent
    
    def is_private(self):
        return False
    
    @staticmethod
    def get_or_create_other_location(border_station):
        try:
            location = Location.objects.get(border_station=border_station, name=Location.other_name)
        except ObjectDoesNotExist:
            location = Location()
            location.name = Location.other_name
            location.border_station = border_station
            location.active = False
            location.location_type = 'monitoring'
            location.save()
        
        return location
    
    @staticmethod
    def get_or_create_leave_location(border_station):
        try:
            location = Location.objects.get(border_station=border_station, name=Location.leave_name)
        except ObjectDoesNotExist:
            location = Location()
            location.name = Location.leave_name
            location.border_station = border_station
            location.active = False
            location.location_type = 'monitoring'
            location.save()
        
        return location
  
class WorksOnProject(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    border_station = models.ForeignKey(BorderStation, on_delete=models.CASCADE)
    work_percent = models.PositiveIntegerField()
    
    class Meta:
       unique_together = ("staff", "border_station")
    
    def set_parent(self, parent):
        self.staff = parent

class StaffProject(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    border_station = models.ForeignKey(BorderStation, on_delete=models.CASCADE)
    coordinator = models.CharField(max_length=127, blank=True)
    receives_money_distribution_form = models.BooleanField(default=False)
    
    class Meta:
       unique_together = ("staff", "border_station")
       abstract = False
    
    def set_parent(self, parent):
        self.staff = parent
    
    def get_country_id(self):
        return staff.get_country_id()
    
    def get_staff_projects(self):
        return staff.get_staff_projects()

class StaffAttachment(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    attachment = models.FileField(upload_to='staff_attachment', default='', blank=True)
    option = models.CharField(max_length=126, null=True)
    attach_date = models.DateField(auto_now_add=True)
    expiration_date = models.DateField(null=True)
    description = models.CharField(max_length=126, null=True)
    
    def get_country_id(self):
        return staff.get_country_id()
    
    def get_staff_projects(self):
        return staff.get_staff_projects()
    


