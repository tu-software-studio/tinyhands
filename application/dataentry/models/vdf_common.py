from django.db import models

from .person import Person
from .form import BaseCard, BaseForm

# Class to store an instance of the VDF data.
# This should contain data that is common for all VDFs and is not expected to be changed
class VdfCommon(BaseForm):
    # Top Box
    vdf_number = models.CharField('IRF #:', max_length=20, unique=True)
    staff_name = models.CharField('Staff Name:', max_length=255)
    interview_date = models.DateField('Interview date', null=True)
    location = models.CharField('Location:', max_length=255)
    
    # Victim/Family Info
    victim = models.ForeignKey(Person, null=True, blank=True, on_delete=models.CASCADE)
    relationship_to_guardian = models.CharField(max_length=126, null=True)
    
    # Recruitment for PVF
    # Recruiting agency/brokers in many to many relationship declared in Suspect model
    pv_recruited_no = models.CharField(max_length=126, null=True)
    pv_recruited_agency = models.CharField(max_length=126, null=True)
    pv_recruited_broker = models.CharField(max_length=126, null=True)
    recruited_agency_name = models.CharField(max_length=126, null=True)
    recruited_broker_names = models.CharField(max_length=126, null=True)
    pv_recruited_how =  models.CharField(max_length=1024, null=True)
    pv_expenses_paid_how = models.CharField(max_length=126, null=True)
    pv_paid_broker_amount =  models.CharField(max_length=126, null=True)
    pv_paid_broker_currency =  models.CharField(max_length=126, null=True)
    broker_paid_amount =  models.CharField(max_length=126, null=True)
    broker_paid_currency =  models.CharField(max_length=126, null=True)
    pv_left_home_date = models.DateField(null=True)
    job_promised  =  models.CharField(max_length=126, null=True)
    job_promised_amount  =  models.CharField(max_length=126, null=True)
    job_promised_currency  =  models.CharField(max_length=126, null=True)
    
    # Travel for PVF
    pv_traveled_how = models.CharField(max_length=126, null=True)
    pv_thinks_they_were_trafficked = models.CharField(max_length=126, null=True)
    
    # Exploitation for PVF
    exploit_prostitution = models.BooleanField(default=False)
    exploit_prostitution_began_years = models.CharField(max_length=126, null=True)
    exploit_prostitution_began_days = models.CharField(max_length=126, null=True)
    exploit_prostitution_lasted_years = models.CharField(max_length=126, null=True)
    exploit_prostitution_lasted_days = models.CharField(max_length=126, null=True)
    exploit_prostitution_explain = models.CharField(max_length=1024, null=True)
    exploit_prostitution_suspects = models.CharField(max_length=1024, null=True)

    exploit_sexual_abuse = models.BooleanField(default=False)
    exploit_sexual_abuse_began_years = models.CharField(max_length=126, null=True)
    exploit_sexual_abuse_began_days = models.CharField(max_length=126, null=True)
    exploit_sexual_abuse_lasted_years = models.CharField(max_length=126, null=True)
    exploit_sexual_abuse_lasted_days = models.CharField(max_length=126, null=True)
    exploit_sexual_abuse_explain = models.CharField(max_length=1024, null=True)
    exploit_sexual_abuse_suspects = models.CharField(max_length=1024, null=True)
    
    exploit_physical_abuse = models.BooleanField(default=False)
    exploit_physical_abuse_began_years = models.CharField(max_length=126, null=True)
    exploit_physical_abuse_began_days = models.CharField(max_length=126, null=True)
    exploit_physical_abuse_lasted_years = models.CharField(max_length=126, null=True)
    exploit_physical_abuse_lasted_days = models.CharField(max_length=126, null=True)
    exploit_physical_abuse_explain = models.CharField(max_length=1024, null=True)
    exploit_physical_abuse_suspects = models.CharField(max_length=1024, null=True)
    
    exploit_debt_bondage = models.BooleanField(default=False)
    exploit_debt_bondage_began_years = models.CharField(max_length=126, null=True)
    exploit_debt_bondage_began_days = models.CharField(max_length=126, null=True)
    exploit_debt_bondage_lasted_years = models.CharField(max_length=126, null=True)
    exploit_debt_bondage_lasted_days = models.CharField(max_length=126, null=True)
    exploit_debt_bondage_explain = models.CharField(max_length=1024, null=True)
    exploit_debt_bondage_suspects = models.CharField(max_length=1024, null=True)
    
    exploit_forced_labor = models.BooleanField(default=False)
    exploit_forced_labor_began_years = models.CharField(max_length=126, null=True)
    exploit_forced_labor_began_days = models.CharField(max_length=126, null=True)
    exploit_forced_labor_lasted_years = models.CharField(max_length=126, null=True)
    exploit_forced_labor_lasted_days = models.CharField(max_length=126, null=True)
    exploit_forced_labor_explain = models.CharField(max_length=1024, null=True)
    exploit_forced_labor_suspects = models.CharField(max_length=1024, null=True)
    
    exploit_other = models.CharField(max_length=126, null=True)
    exploit_other_began_years = models.CharField(max_length=126, null=True)
    exploit_other_began_days = models.CharField(max_length=126, null=True)
    exploit_other_lasted_years = models.CharField(max_length=126, null=True)
    exploit_other_lasted_days = models.CharField(max_length=126, null=True)
    exploit_other_explain = models.CharField(max_length=1024, null=True)
    exploit_other_suspects = models.CharField(max_length=1024, null=True)
    
    # Home Situation Assessment
    guardian_know_destination = models.CharField('Did your guardian know you were traveling to intended destination?', max_length=126, null=True)
    family_guardian_pressure = models.CharField("Did your family/guardian pressure you in any way to accept the broker's offer?", max_length=126, null=True)
    try_to_send_overseas_again = models.CharField('If they attempted, do you think they will try to send you overseas again?', max_length=126, null=True)
    feel_safe_with_guardian = models.CharField('Do you feel safe at home with your guardian?', max_length=126, null=True)
    do_you_want_to_go_home = models.CharField('Do you want to go home?', max_length=126, null=True)
    sexual_abuse = models.CharField('Sexual Abuse', max_length=126, null=True)
    physical_abuse = models.CharField('Physical Abuse', max_length=126, null=True)
    emotional_abuse = models.CharField('Emotional Abuse', max_length=126, null=True)
    guardian_drink_alcohol = models.CharField('Does the Guardian drink alcohol?', max_length=126, null=True)
    guardian_use_drugs = models.CharField('Does the Guardian use drugs?', max_length=126, null=True)
    family_economic_situation = models.CharField('Economic Situation of Family', max_length=126, null=True)
    express_suicidal_thoughts = models.CharField('Did the victim express any suicidal thoughts at any point?', max_length=126, null=True)
    total_situational_alarms = models.PositiveIntegerField('Total Situational Alarms', null=True, blank=True)
    station_recommendation_for_victim = models.CharField('What is the Border Station recommendation about where the victim should go?', max_length=126, null=True)
    is_evidence_that_guardians_sold = models.CharField('Did the victim express any suicidal thoughts at any point?', max_length=126, null=True)
    evidence_that_guardians_sold = models.CharField('If yes, what evidence?', max_length=126, null=True)
    contact_national_office = models.CharField(max_length=126, null=True)
    why_sent_home_with_with_alarms = models.TextField('If the potential victim has 10 or more total Home Situation Alarms and you recommend sending the potential victim home to stay with guardians, why?', null=True)


    # Awareness/Assessment
    staff_share_gospel = models.CharField('Did the staff share the gospel with the victim?', max_length=126, null=True)
    share_gospel_film = models.BooleanField('Film', default=False)
    share_gospel_tract = models.BooleanField('Tract', default=False)
    share_gospel_oral = models.BooleanField('Oral Preaching', default=False)
    share_gospel_testimony = models.BooleanField('Shared Personal Testimony', default=False)
    share_gospel_book = models.BooleanField('Message Book', default=False)
    share_gospel_resource = models.BooleanField('Used a resource', default=False)
    share_gospel_other = models.CharField('Other', max_length=126, null=True)
    share_gospel_why_not = models.TextField(blank=True)
    share_gospel_connect_to_local_church = models.TextField(blank=True)
    share_gospel_give_pv = models.CharField(max_length=126, null=True)
    awareness_of_exploitation_before_interception = models.CharField('Before you were intercepted, were you aware that migrants going abroad are often deceived and end up in very exploitative situations?', max_length=126, null=True)
    victim_heard_message_before = models.CharField('Had you ever heard the message before?', max_length=126, null=True)
    what_victim_believes_now = models.CharField('What do you believe now?', max_length=126, null=True)
    victim_testimony = models.TextField(blank=True)
    transit_staff_polite = models.PositiveIntegerField('Transit Staff Polite and Respectful', null=True, blank=True)
    trafficking_awareness = models.PositiveIntegerField('Trafficking Awareness', null=True, blank=True)
    shelter_staff_polite = models.PositiveIntegerField('Shelter Staff Polite and Respectful', null=True, blank=True)
    shelter_accomodation = models.PositiveIntegerField('Shelter Accomodations', null=True, blank=True)
    
    # Release Information
    date_victim_left = models.DateField('What date did victim leave the care of the Station', null=True)
    someone_pick_up_victim = models.CharField('Did someone pick up victim from the station?', max_length=126, null=True)
    who_victim_released = models.CharField('If yes, who was the victim released to?', max_length=126, null=True)
    who_victim_released_name = models.CharField('Name of person whom the victim was released to', max_length=126, null=True)
    who_victim_released_phone = models.CharField('Phone Number', max_length=126, null=True)
    where_victim_sent = models.CharField('Where was the victim sent', max_length=126, null=True)
    where_victim_sent_details = models.CharField('Where was the victim sent details', max_length=126, null=True)
    how_pv_released =  models.CharField(max_length=126, null=True)
    service_education_about_ht = models.BooleanField('Education about HT', default=False)
    service_legal_support = models.BooleanField('Legal Support', default=False)
    service_medical_support = models.BooleanField('Medical Support ', default=False)
    service_travel_support = models.BooleanField('Travel Support', default=False)
    service_food = models.BooleanField('Food', default=False)
    service_safe_foreign_employment = models.BooleanField('Safe Foreign Employment Info', default=False)
    country_pv_sent = models.CharField('What country was the PV sent back to?', max_length=126, null=True)
    pv_spent_time_at_shelter = models.CharField('Did the PV spend time at LJ’s short-term shelter?', max_length=126, null=True)
    shelter_nights = models.PositiveIntegerField('nights', null=True, blank=True)
    interaction_hours = models.PositiveIntegerField('hours', null=True, blank=True)
    overnight_lodging = models.CharField(max_length=126, null=True)
    other_shelter  = models.CharField(max_length=126, null=True)

    # Final Procedures
    fundraising_purpose = models.CharField('how we can use your photo and the information collected during this interviewfor operational fundraising purposes.', max_length=126, null=True)
    consent_to_use_information = models.CharField('I give consent to use any information I have shared throughout the duration of my time with the staff for operational and awareness purposes', max_length=126, null=True)
    consent_to_use_photo = models.CharField('Do you consent to us using your photo this way?', max_length=126, null=True)
    victim_signature = models.BooleanField('Victim Signature', default=False)
    guardian_signature = models.BooleanField('Guardian Signature', default=False)
    case_notes = models.TextField('Case Notes', blank=True)
    
    #Logbook
    logbook_received = models.DateField(null=True)
    logbook_incomplete_questions = models.CharField(max_length=127, blank=True)
    logbook_incomplete_sections = models.CharField(max_length=127, blank=True)
    logbook_information_complete = models.DateField(null=True)
    logbook_notes = models.TextField('Logbook Notes', blank=True)
    logbook_submitted = models.DateField(null=True)
    
    def get_key(self):
        return self.vdf_number
    
    def get_form_type_name(self):
        return 'VDF'
    
    def get_form_date(self):
        return self.interview_date
    
    @staticmethod
    def key_field_name():
        return 'vdf_number'
    
    class Meta:
        indexes = [
            models.Index(fields=['logbook_submitted', 'station'])
        ]

class VdfAttachmentCommon(BaseCard):
    attachment_number = models.PositiveIntegerField(null=True, blank=True)
    description = models.CharField(max_length=126, null=True)
    attachment = models.FileField('Attach scanned copy of form (pdf or image)', upload_to='vdf_attachments')
    private_card = models.BooleanField(default=True)
    option = models.CharField(max_length=126, null=True)
    vdf = models.ForeignKey(VdfCommon, on_delete=models.CASCADE)
    
    def set_parent(self, the_parent):
        self.vdf = the_parent
        
    def is_private(self):
        return self.private_card
    
class GospelVerification(BaseForm):
    vdf = models.ForeignKey(VdfCommon, on_delete=models.CASCADE)
    searchlight_edited = models.CharField(max_length=126, null=True)
    form_changes = models.CharField(max_length=126, null=True)
    reason_for_change = models.TextField(null=True)
    staff_who_shared = models.CharField(max_length=126, null=True)
    how_pv_professed = models.TextField(null=True)
    shared_resources = models.TextField(null=True)
    connect_with_church = models.TextField(null=True)
    date_of_followup = models.DateField('Interview date', null=True)
    followup_person = models.CharField(max_length=126, null=True)
    
    @property
    def profess_to_accept_christ(self):
        if self.date_of_followup is not None:
            if (self.vdf.what_victim_believes_now == 'Came to believe that Jesus is the one true God'
                or self.vdf.what_victim_believes_now == 'Already believes Jesus is the one true God'):
                return 'Yes'
            else:
                return 'No'
        
        return ''
    
    def get_key(self):
        return self.vdf.vdf_number
