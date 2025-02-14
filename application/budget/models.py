import uuid
from datetime import datetime

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

from accounts.models import Account
from dataentry.models import BorderStation
from static_border_stations.models import Staff
import budget.mdf_constants as constants

class BorderStationBudgetCalculation(models.Model):
    TRAVEL = 1
    MISCELLANEOUS = 2
    AWARENESS = 3
    POTENTIAL_VICTIM_CARE = 5
    COMMUNICATION = 7
    STAFF_BENEFITS = 8
    ADMINISTRATION = 10
    PAST_MONTH_SENT = 11
    LIMBO = 12
    MONEY_NOT_SPENT = 13
    IMPACT_MULTIPLYING = 14
    RENT_UTILITIES = 15

    mdf_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    date_time_entered = models.DateTimeField(auto_now_add=True)
    date_time_last_updated = models.DateTimeField(auto_now=True)
    date_finalized = models.DateField(null=True)

    month_year = models.DateTimeField(default=datetime.now)

    border_station = models.ForeignKey(BorderStation, on_delete=models.CASCADE)
    mdf_combined = GenericRelation('MdfCombined')

    def other_project_items_total(self, section, project):
        items = self.otherbudgetitemcost_set.filter(form_section=section, work_project=project).exclude(cost__isnull=True)
        return sum(item.cost for item in items)
    
    def staff_project_items_total(self, the_type, project):
        items = self.staffbudgetitem_set.filter(type_name=the_type,work_project=project).exclude(cost__isnull=True)
        return sum(item.cost for item in items)
    
    def staff_salary_and_benefits_deductions(self, project):
        total = sum([staff.cost for staff in self.staffbudgetitem_set.filter(work_project=project, type_name='Deductions').exclude(cost__isnull=True)])
        return total
    
    def staff_salary_and_benefits_total(self, project):
        total = sum([staff.cost for staff in self.staffbudgetitem_set.filter(work_project=project).
                     exclude(cost__isnull=True).exclude(type_name='Travel').exclude(type_name='Deductions')])
        total -= self.staff_salary_and_benefits_deductions(project)
        return total
    
    def salary_and_benefits_extra_items_total(self, project):
        total = self.other_project_items_total(self.STAFF_BENEFITS, project)
        return total
    
    def salary_and_benefits_total(self, project):
        total = self.staff_salary_and_benefits_total(project) + self.salary_and_benefits_extra_items_total(project)
        return total
    
    booth = models.BooleanField('Booth', default=False)
    booth_amount = models.DecimalField(max_digits=17, decimal_places=2, default=30000)
    office = models.BooleanField('Office', default=False)
    office_amount = models.DecimalField(max_digits=17, decimal_places=2, default=2000)
    
    def rent_and_utilities_extra_total(self):
        total = self.other_project_items_total(self.RENT_UTILITIES, self.border_station)
        return total
    
    def rent_and_utilities_total(self):
        total = self.rent_and_utilities_extra_total()
        if self.booth:
            total += self.booth_amount
        if self.office:
            total += self.office_amount
        return total

    communication_chair = models.BooleanField(default=False)
    communication_chair_amount = models.DecimalField('for chair', max_digits=17, decimal_places=2, default=1000)
    
    def communication_manager_chair_total(self):
        total = 0
        if self.communication_chair:
            total += self.communication_chair_amount
        return total
    
    travel_chair = models.BooleanField(default=False)
    travel_chair_amount = models.DecimalField('for chair (if has bike)', max_digits=17, decimal_places=2, default=2000)

    def travel_manager_chair_total(self):
        total = 0
        if self.travel_chair:
            total += self.travel_chair_amount
        return total

    number_of_intercepts_last_month = models.PositiveIntegerField('# of intercepts last month', default=0)
    number_of_intercepts_last_month_multiplier = models.DecimalField(max_digits=17, decimal_places=2, default=20)
    number_of_intercepts_last_month_adder = models.DecimalField(max_digits=17, decimal_places=2, default=1000)
    number_of_meetings_per_month = models.PositiveIntegerField('# of meetings per month', default=0)
    number_of_meetings_per_month_multiplier = models.DecimalField(max_digits=17, decimal_places=2, default=600)
    

    def administration_intercepts_total(self):
        return self.number_of_intercepts_last_month * self.number_of_intercepts_last_month_multiplier + self.number_of_intercepts_last_month_adder

    def administration_meetings_total(self):
        return self.number_of_meetings_per_month * self.number_of_meetings_per_month_multiplier

    def administration_extra_items_total(self):
        return self.other_project_items_total(self.ADMINISTRATION, self.border_station)

    def administration_total(self):
        total = 0
        total += self.administration_intercepts_total()
        total += self.administration_meetings_total()
        total += self.travel_manager_chair_total()
        total += self.communication_manager_chair_total();
        return total + self.administration_extra_items_total()

    def travel_extra_items_total(self):
        return self.other_project_items_total(self.TRAVEL, self.border_station)

    def travel_total(self):
        total = 0
        total += self.travel_extra_items_total()
        total += self.staff_project_items_total('Travel', self.border_station)
        return total
    
    def staff_travel_total(self):
        total = self.staff_project_items_total('Travel', self.border_station)
        total += staff.travel_extra_items_total()
        return total
    
    shelter_rent = models.BooleanField('Rent', default=False)
    shelter_rent_amount = models.DecimalField(max_digits=17, decimal_places=2, default=0)
    shelter_water = models.BooleanField('Water', default=False)
    shelter_water_amount = models.DecimalField(max_digits=17, decimal_places=2, default=0)
    shelter_electricity = models.BooleanField('Electricity', default=False)
    shelter_electricity_amount = models.DecimalField(max_digits=17, decimal_places=2, default=0)

    def shelter_total(self):
        total = 0
        if self.shelter_rent:
            total += self.shelter_rent_amount
        if self.shelter_water:
            total += self.shelter_water_amount
        if self.shelter_electricity:
            total += self.shelter_electricity_amount
        return total
    
    def pv_extra_items_total(self):
        return self.other_project_items_total(self.POTENTIAL_VICTIM_CARE, self.border_station)
    
    def pv_total(self):
        return self.shelter_total() + self.food_and_gas_total() + self.pv_extra_items_total()

    number_of_intercepted_pvs = models.PositiveIntegerField('# of intercepted girls', default=0)
    food_per_pv_amount = models.DecimalField(max_digits=17, decimal_places=2, default=100)
    number_of_pv_days = models.PositiveIntegerField(default=3)
    limbo_girls_multiplier = models.DecimalField(max_digits=17, decimal_places=2, default=100)

    def food_and_gas_intercepted_girls_total(self):
        return self.number_of_intercepted_pvs * self.food_per_pv_amount * self.number_of_pv_days

    def food_and_gas_limbo_girls_total(self):
        return self.limbo_girls_multiplier * self.other_project_items_total(self.LIMBO, self.border_station)

    def food_and_gas_total(self):
        total = 0
        total += self.food_and_gas_intercepted_girls_total()
        total += self.food_and_gas_limbo_girls_total()
        return total

    contact_cards = models.BooleanField('Contact Cards', default=False)
    contact_cards_amount = models.DecimalField(max_digits=17, decimal_places=2, default=0)
    awareness_party_boolean = models.BooleanField("Awareness Party", default=False)
    awareness_party = models.DecimalField(max_digits=17, decimal_places=2, default=0)

    def awareness_extra_items_total(self):
        return self.other_project_items_total(self.AWARENESS, self.border_station)

    def awareness_total(self):
        total = self.awareness_extra_items_total()
        if self.contact_cards:
            total += self.contact_cards_amount
        if self.awareness_party_boolean:
            total += self.awareness_party
        return total
    
    def supplies_and_awareness_total(self):
        total = self.awareness_extra_items_total()
        if self.contact_cards:
            total += self.contact_cards_amount
        if self.awareness_party_boolean:
            total += self.awareness_party
        return total
      
    def money_not_spent_to_deduct_total(self, project):
        items = self.otherbudgetitemcost_set.filter(form_section=self.MONEY_NOT_SPENT, deduct='Yes', work_project=project).exclude(cost__isnull=True)
        return sum(item.cost for item in items)
    
    past_sent_approved = models.CharField(max_length=127, blank=True)
    
    def past_month_sent_total(self, project):
        return self.other_project_items_total(self.PAST_MONTH_SENT, project)
    
    def impact_multiplying_total(self, project):
        return self.other_project_items_total(self.IMPACT_MULTIPLYING, project)

    def station_total(self, project):
        total = 0
        total += self.salary_and_benefits_total(project)
        if project == self.border_station:
            total += self.awareness_total()
            total += self.pv_total()
            total += self.administration_total()
            total += self.travel_total()
            total += self.rent_and_utilities_total()
        else:
            total += self.impact_multiplying_total(project)
        return total
    
    notes = models.TextField('Notes', blank=True)

    def mdf_file_name(self):
        return '{}-{}-{}-MDF.pdf'.format(self.border_station.station_code, self.month_year.month, self.month_year.year)

    def get_country_id(self):
        if self.border_station is None or self.border_station.operating_country is None:
            return None
        return self.border_station.operating_country.id  
    
    def get_border_station_id(self):
        if self.border_station is None:
            return None
        return self.border_station.id
    
    def __str__(self):
        return "{} - {}".format(self.border_station.station_name, self.month_year)


class OtherBudgetItemCost(models.Model):

    BUDGET_FORM_SECTION_CHOICES = [
        (BorderStationBudgetCalculation.TRAVEL, 'Staff Travel'),
        (BorderStationBudgetCalculation.MISCELLANEOUS, 'Miscellaneous'),
        (BorderStationBudgetCalculation.AWARENESS, 'Awareness'),
        (BorderStationBudgetCalculation.POTENTIAL_VICTIM_CARE, 'Potential Victim Care'),
        (BorderStationBudgetCalculation.COMMUNICATION, 'Communication'),
        (BorderStationBudgetCalculation.STAFF_BENEFITS, 'Salaries & Benefits'),
        (BorderStationBudgetCalculation.ADMINISTRATION, 'Administration'),
        (BorderStationBudgetCalculation.PAST_MONTH_SENT, 'Past Month Sent Money'),
        (BorderStationBudgetCalculation.LIMBO, 'Limbo Potential Victims'),
        (BorderStationBudgetCalculation.MONEY_NOT_SPENT, 'Money Not Spent'),
        (BorderStationBudgetCalculation.IMPACT_MULTIPLYING, 'Operational Expenses'),
        (BorderStationBudgetCalculation.RENT_UTILITIES, 'Rent & Utilities'),
    ]
    name = models.CharField(max_length=255, blank=False)
    cost = models.DecimalField(max_digits=17, decimal_places=2, default=0, blank=False)
    form_section = models.IntegerField(BUDGET_FORM_SECTION_CHOICES, blank=True, null=True)
    budget_item_parent = models.ForeignKey(BorderStationBudgetCalculation, blank=True, null=True, on_delete=models.CASCADE)
    associated_section = models.IntegerField(BUDGET_FORM_SECTION_CHOICES, blank=True, null=True)
    deduct = models.CharField(max_length=255, blank=True, null=True)
    work_project = models.ForeignKey(BorderStation, null=True, on_delete=models.CASCADE)
    
    def get_country_id(self):
        if self.budget_item_parent is None or self.budget_item_parent.border_station is None or self.budget_item_parent.border_station.operating_country is None:
            return None
        return self.budget_item_parent.border_station.operating_country.id  
    
    def get_border_station_id(self):
        if self.budget_item_parent is None or self.budget_item_parent.border_station is None:
            return None
        return self.budget_item_parent.border_station.id


class StaffBudgetItem(models.Model):
    budget_calc_sheet = models.ForeignKey(BorderStationBudgetCalculation, blank=True, null=True, on_delete=models.CASCADE)
    staff_person = models.ForeignKey(Staff, blank=True, null=True, on_delete=models.CASCADE)
    type_name = models.CharField(max_length=255, blank=False)
    description = models.TextField('Description', blank=True)
    cost = models.DecimalField(max_digits=17, decimal_places=2, default=0, blank=True, null=True)
    work_project = models.ForeignKey(BorderStation, null=True, on_delete=models.CASCADE)
    
    class Meta:
       unique_together = ("budget_calc_sheet", "staff_person", 'type_name', 'work_project')
    
    def get_country_id(self):
        if self.budget_calc_sheet is None or self.budget_calc_sheet.border_station is None or self.budget_calc_sheet.border_station.operating_country is None:
            return None
        return self.budget_calc_sheet.border_station.operating_country.id  
    
    def get_border_station_id(self):
        if self.budget_calc_sheet is None or self.budget_calc_sheet.border_station is None:
            return None
        return self.budget_calc_sheet.border_station.id



class MonthlyDistributionMultipliers(models.Model):
    name = models.CharField(max_length=127)             # name/description to identify in Project Request
    category = models.IntegerField(constants.CATEGORY_CHOICES)    # MDF category in which it appears 
    
class ProjectRequest(models.Model):
    date_time_entered = models.DateTimeField(auto_now_add=True)
    date_time_last_updated = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(Account, null=True, on_delete=models.SET_NULL)  # Original author
    
    project = models.ForeignKey(BorderStation, on_delete=models.CASCADE)
    status = models.CharField(max_length=127, default='Submitted')
    category = models.IntegerField(constants.REQUEST_CATEGORY_CHOICES_MDF)
    original_cost = models.DecimalField(max_digits=17, decimal_places=2, default=0, blank=False)
    cost = models.DecimalField(max_digits=17, decimal_places=2, default=0, blank=False)
    description = models.TextField('Description', blank=True)
    monthly = models.BooleanField('Monthly', default=False)
    staff = models.ForeignKey(Staff, null=True, on_delete=models.SET_NULL)
    benefit_type_name = models.CharField(max_length=127, blank=True)
    discussion_status =  models.CharField(max_length=127, default='None')
    prior_request = models.ForeignKey('self', null=True, on_delete=models.CASCADE)
    override_mdf_project = models.ForeignKey(BorderStation, null=True, on_delete=models.CASCADE,
                                             related_name="override_mdf")
    completed_date_time = models.DateTimeField(null=True)
    
    def get_country_id(self):
        return self.project.operating_country.id
    
    def get_border_station_id(self):
        return self.project.id
    
    @property
    def category_name(self):
        name='Unknown'
        for category in constants.CATEGORY_CHOICES:
            if self.category == category[0]:
                name = category[1]
        return name
    
    @property
    def monthly_string(self):
        if self.monthly:
            return 'Y'
        else:
            return 'N'
        

class ProjectRequestDiscussion(models.Model):
    request = models.ForeignKey(ProjectRequest, on_delete=models.CASCADE)
    author = models.ForeignKey(Account, null=True, on_delete=models.SET_NULL)
    date_time_entered = models.DateTimeField(auto_now_add=True)
    text = models.TextField('Discussion text', blank=True)
    notify = models.ManyToManyField(Account, related_name="discussion_notify")
    response = models.ManyToManyField(Account, related_name="discussion_response") # notified accounts that have responded
    
    def get_country_id(self):
        return self.request.project.operating_country.id
    
    def get_border_station_id(self):
        return self.request.project.id
    
class ProjectRequestAttachment(models.Model):
    request = models.ForeignKey(ProjectRequest, on_delete=models.CASCADE)
    description = models.CharField(max_length=126, null=True)
    attachment = models.FileField(upload_to='project_request_attachments')
    option = models.CharField(max_length=127, null=True)    # Type of attachment
    
    def get_country_id(self):
        return self.request.project.operating_country.id
    
    def get_border_station_id(self):
        return self.request.project.id


    
class MonthlyDistributionForm(models.Model):
    date_time_entered = models.DateTimeField(auto_now_add=True)
    date_time_last_updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=127, default='Submitted')
    # Don't really need date time object, but need the same filed type as
    # BorderStationBudgetCalculation to be able to sort them together
    month_year = models.DateTimeField(default=datetime.now)
    border_station = models.ForeignKey(BorderStation, on_delete=models.CASCADE)
    
    last_month_number_of_intercepted_pvs = models.PositiveIntegerField('# last month PVs', default=0)
    number_of_pv_days = models.PositiveIntegerField(default=0)
    past_sent_approved = models.CharField(max_length=127, blank=True)
    past_month_sent_reviewed = models.BooleanField(default=False)
    money_not_spent_reviewed = models.BooleanField(default=False)
    notes = models.TextField('Notes', blank=True)
    
    requests = models.ManyToManyField(ProjectRequest)
    signed_pbs = models.FileField(upload_to='pbs_attachments', default='', blank=True)
    mdf_combined = GenericRelation('MdfCombined')
    
    def include_request(self, request):
        result = False
        if request.status == 'Approved':
            result = True
        elif request.status =='Approved-Completed' and request.completed_date_time > self.month_year:
            result = True
        return result
        
    
    def salary_and_benefits_total(self, project):
        total = 0
        requests = self.requests.filter(project=project, category=constants.STAFF_BENEFITS).exclude(cost__isnull=True)
        for request in requests:
            if self.include_request(request):
                if request.benefit_type_name == 'Deductions':
                    total -= request.cost
                else:
                    total += request.cost
            
        return total
    
    def staff_salary_and_benefits_deductions(self, project):
        total = 0
        requests = self.requests.filter(project=project, category=constants.STAFF_BENEFITS, benefit_type_name='Deductions').exclude(cost__isnull=True)
        for request in requests:
            if request.status == 'Approved-Completed' and request.completed_date_time < self.month_year:
                continue
            total += request.cost
            
        return total
        
    
    def rent_and_utilities_total(self):
        total = 0
        requests = self.requests.filter(project=self.border_station, category=constants.RENT_UTILITIES).exclude(cost__isnull=True)
        for request in requests:
            if self.include_request(request):
                total += request.cost
        return total
    
    def administration_total(self):
        total = 0
        requests = self.requests.filter(project=self.border_station, category=constants.ADMINISTRATION).exclude(cost__isnull=True)
        for request in requests:
            if self.include_request(request):
                total += request.cost
        return total
    
    def stationery_total(self):
        total = 0
        multiplier_type = MonthlyDistributionMultipliers.objects.get(category=constants.AWARENESS)
        
        multipliers = self.requests.filter(project=self.border_station, category=constants.MULTIPLIERS,
                                          description=multiplier_type.name).exclude(cost__isnull=True)
        for multiplier in multipliers:
            if self.include_request(multiplier):
                total += multiplier.cost * self.last_month_number_of_intercepted_pvs
                break
        return total  
        
    
    def awareness_total(self):
        total = 0
        requests = self.requests.filter(project=self.border_station, category=constants.AWARENESS).exclude(cost__isnull=True)
        for request in requests:
            if self.include_request(request):
                total += request.cost
        
        return total  
    
    def travel_total(self):
        total = 0
        requests = self.requests.filter(project=self.border_station, category=constants.TRAVEL).exclude(cost__isnull=True)
        for request in requests:
            if self.include_request(request):
                total += request.cost
        return total
    
    def food_and_snacks_intercepted_pv_total(self):
        total = 0
        
        if self.number_of_pv_days > 0:
            pv_multiplier_type = MonthlyDistributionMultipliers.objects.get(category=constants.POTENTIAL_VICTIM_CARE)
            multipliers = self.requests.filter(project=self.border_station, category=constants.MULTIPLIERS,
                                          description=pv_multiplier_type.name).exclude(cost__isnull=True)
            for multiplier in multipliers:
                if self.include_request(multiplier):
                    total += multiplier.cost * self.number_of_pv_days
                    break
        return total
    
    @property
    def limbo_girls_multiplier(self):
        multiplier_value = 0
        limbo_multiplier_type = MonthlyDistributionMultipliers.objects.get(category=constants.LIMBO)
        multipliers = self.requests.filter(project=self.border_station, category=constants.MULTIPLIERS,
                                          description=limbo_multiplier_type.name).exclude(cost__isnull=True)
        for multiplier in multipliers:
            if self.include_request(multiplier):
                multiplier_value = multiplier.cost
                break
        return multiplier_value
    
    def limbo_total(self):
        total = 0
        
        limbo_pvs = self.mdfitem_set.filter(work_project=self.border_station, category=constants.LIMBO).exclude(cost__isnull=True)
        limbo_pv_days = 0
        for limbo_pv in limbo_pvs:
            limbo_pv_days += limbo_pv.cost
            
        if limbo_pv_days > 0:
            total += self.limbo_girls_multiplier * limbo_pv_days
                    
        return total
    
    def pv_total(self):
        total = 0
        requests = self.requests.filter(project=self.border_station, category=constants.POTENTIAL_VICTIM_CARE).exclude(cost__isnull=True)
        for request in requests:
            if self.include_request(request):
                total += request.cost
            
        return total
    
    def impact_multiplying_total(self, project):
        total = 0
        requests = self.requests.filter(project=project, category=constants.IMPACT_MULTIPLYING).exclude(cost__isnull=True)
        for request in requests:
            if self.include_request(request):
                total += request.cost
        return total
    
    def money_not_spent_to_deduct_total(self, project):
        total = 0
        to_deduct_qs = self.mdfitem_set.filter(work_project=project, category=constants.MONEY_NOT_SPENT, deduct='Yes').exclude(cost__isnull=True)
        for to_deduct in to_deduct_qs:
            total += to_deduct.cost
        return total
    
    def money_not_spent_not_deduct_total(self, project):
        total = 0
        to_deduct_qs = self.mdfitem_set.filter(work_project=project, category=constants.MONEY_NOT_SPENT, deduct='No').exclude(cost__isnull=True)
        for to_deduct in to_deduct_qs:
            total += to_deduct.cost
        return total

    
    def station_total(self, project):
        total = 0
        total += self.salary_and_benefits_total(project)
        if project == self.border_station:
            total += self.rent_and_utilities_total()
            total += self.administration_total()
            total += self.awareness_total()
            total += self.travel_total()
            total += self.pv_total()
        else:
            total += self.impact_multiplying_total(project)
         
        print('total',total)   
        return total
    
    def distribution_total(self, project):
        return self.station_total(project) - self.money_not_spent_to_deduct_total(project)
    
    def full_total(self, project):
        total = self.distribution_total(project) + self.staff_salary_and_benefits_deductions(project)
        past_sent_list = self.mdfitem_set.filter(work_project=project, category=constants.PAST_MONTH_SENT)
        for past_sent in past_sent_list:
            total += past_sent.cost
        return total
    
    @staticmethod
    def guide_total(border_station, year, month, category, subcategory):
        total = 0
        try:
            mdf = MonthlyDistributionForm.objects.get(
                border_station=border_station,
                month_year__year = year,
                month_year__month = month)    
        except:
            return total
        
        requests = mdf.requests.filter(category=category, benefit_type_name=subcategory)
        for request in requests:
            total = total + request.cost
        return total
        
    @property
    def guide_progress_old(self):
        result = {}
        
        guides = self.requests.filter(category=constants.GUIDES)
        for guide in guides:
            year = self.month_year.year
            month = self.month_year.month
            if guide.description == 'PV Food':
                category = constants.POTENTIAL_VICTIM_CARE
            elif guide.description == 'Stationery':
                 category = constants.AWARENESS
    
            else:
                # Unknown guide
                continue
            result[guide.description] = {"guide":guide.cost, "months":[], "six_month_total":0}
            for loop in range(0,6):
                if 'Multiplier' in guide.description:
                    try:
                        mdf = MonthlyDistributionForm.objects.get(
                            border_station=self.border_station,
                            month_year__year = year,
                            month_year__month = month)
                        multiplier_total = guide.cost * mdf.last_month_number_of_intercepted_pvs
                    except:
                        multiplier_total = 0
                    entry = {
                            "year":year,
                            "month":month,
                            "guide":multiplier_total
                        }
                else:
                    entry = {
                            "year":year,
                            "month":month,
                            "total":MonthlyDistributionForm.guide_total(self.border_station, year, month, category, guide.description),
                            "guide":guide.cost
                        }
                result[guide.description]["months"].append(entry)
                result[guide.description]["six_month_total"] += entry['total']
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1

        return result
    
    @property
    def guide_progress(self):
        result = {}
        
        for guide_pair in [{'description':'PV Food', 'category':constants.POTENTIAL_VICTIM_CARE}, {'description':'Stationery', 'category':constants.AWARENESS}]:
            found = False
            year = self.month_year.year
            month = self.month_year.month
            
            months = []
            six_month = {'total':0, 'guide':0}
            for loop in range(0,6):
                entry = {'year':year, 'month':month, 'total':0, 'guide':0}
                
                try:
                    mdf = MonthlyDistributionForm.objects.get(
                        border_station=self.border_station,
                        month_year__year = year,
                        month_year__month = month)
                    
                    base_list = mdf.requests.filter(category=constants.GUIDES, description=guide_pair['description'])
                    multiplier_list = mdf.requests.filter(description=guide_pair['description'] + ' Multiplier')
                    if len(base_list) > 0 or len(multiplier_list) > 0:
                        found = True 
                        if len(base_list) > 0:
                            entry['guide'] += base_list[0].cost
                        if len(multiplier_list) > 0:
                            entry['guide'] += multiplier_list[0].cost * mdf.last_month_number_of_intercepted_pvs
                        entry['total'] = MonthlyDistributionForm.guide_total(self.border_station, year, month,
                                            guide_pair['category'], guide_pair['description'])                  
                except:
                    pass
                
                months.append(entry)
                six_month['total'] += entry['total']
                six_month['guide'] += entry['guide']
        
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1
                    
            if found:
                result[guide_pair['description']] = {'months':months, 'six_month':six_month}          

        return result
    
    def get_country_id(self):
        return self.project.operating_country.id
    
    def get_border_station_id(self):
        return self.project.id
    
    def mdf_file_name(self):
        return '{}-{}-{}-MDF.pdf'.format(self.border_station.station_code, self.month_year.month, self.month_year.year)

class MdfCombined(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    
    month_year = models.DateTimeField(default=datetime.now)
    border_station = models.ForeignKey(BorderStation, on_delete=models.CASCADE)
    status = models.CharField(max_length=127, default='Submitted')
    date_time_entered = models.DateTimeField(auto_now_add=True)
    date_time_last_updated = models.DateTimeField(auto_now=True)
    
@receiver(post_save, sender=MonthlyDistributionForm)
def handle_new_monthly_distribution_form(sender, **kwargs):
    instance = kwargs.get('instance')
    content_type = ContentType.objects.get_for_model(instance)
    try:
        mdf = MdfCombined.objects.get(content_type=content_type, object_id=instance.id)
    except:
        mdf =  MdfCombined()
        mdf.content_type = content_type
        mdf.object_id = instance.id
    
    mdf.month_year = instance.month_year
    mdf.border_station = instance.border_station
    mdf.status = instance.status
    mdf.date_time_entered = instance.date_time_entered
    mdf.date_time_last_updated = instance.date_time_last_updated
    mdf.save()

@receiver(post_save, sender=BorderStationBudgetCalculation)
def handle_new_budget_calculation(sender, **kwargs):
    instance = kwargs.get('instance')
    content_type = ContentType.objects.get_for_model(instance)
    try:
        mdf = MdfCombined.objects.get(content_type=content_type, object_id=instance.id)
    except:
        mdf =  MdfCombined()
        mdf.content_type = content_type
        mdf.object_id = instance.id
    
    mdf.month_year = instance.month_year
    mdf.border_station = instance.border_station
    mdf.date_time_entered = instance.date_time_entered
    mdf.date_time_last_updated = instance.date_time_last_updated
    if instance.date_finalized is None:
        mdf.status = 'Submitted'
    else:
        mdf.status = 'Final'
    mdf.save()
        
    
    

class ProjectRequestComment(models.Model):
    request = models.ForeignKey(ProjectRequest, on_delete=models.CASCADE)
    mdf = models.ForeignKey(MonthlyDistributionForm, on_delete=models.SET_NULL, null=True)
    type =  models.CharField(max_length=127)
    comment = models.TextField('Description', blank=True)
    

# MDF items that are not ProjectRequest items
# e.g. categories PAST_MONTH_SENT, MONEY_NOT_SPENT and LIMBO
class MdfItem(models.Model):
    mdf = models.ForeignKey(MonthlyDistributionForm, on_delete=models.CASCADE)
    
    category = models.IntegerField(constants.MANUAL_CATEGORY_CHOICES)
    cost = models.DecimalField(max_digits=17, decimal_places=2, default=0, blank=False)
    description = models.TextField('Description', blank=True)
    associated_section = models.IntegerField(constants.CATEGORY_CHOICES, blank=True, null=True)
    deduct = models.CharField(max_length=127, blank=True, null=True)
    reason_not_deduct = models.TextField('Reason to not deduct', blank=True)
    work_project = models.ForeignKey(BorderStation, on_delete=models.CASCADE)
    approved_by = models.CharField(max_length=127, blank=True)
    
    def get_country_id(self):
        return self.mdf.project.operating_country.id
    
    def get_border_station_id(self):
        return self.mdf.project.id
    
    def category_name_string(self, category_number):
        name='Unknown'
        for category in constants.CATEGORY_CHOICES:
            if category_number == category[0]:
                name = category[1]
        return name
        
    @property
    def category_name(self):
        return self.category_name_string(self.category)
    
    @property
    def associated_section_name(self):
        name = ''
        if self.associated_section is not None and self.associated_section != '':
            name = self.category_name_string(self.associated_section)
        
        return name

    
    
    

