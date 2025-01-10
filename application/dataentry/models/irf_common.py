from django.db import models
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill

from .person import Person
from .form import BaseCard
from .form import BaseForm
from .form import FormCategory
from accounts.models import Account

# Class to store an instance of the IRF data.
# This should contain data that is common for all IRFs and is not expected to be changed
class IrfCommon(BaseForm):
    # Top Box
    irf_number = models.CharField('IRF #:', max_length=20, unique=True)
    number_of_victims = models.PositiveIntegerField('# of victims:', null=True, blank=True)
    location = models.CharField('Location:', max_length=255)
    date_of_interception = models.DateField('Interception date', null=True, default=None)
    time_of_interception = models.TimeField(null=True)
    number_of_traffickers = models.PositiveIntegerField('# of traffickers', null=True, blank=True)
    staff_name = models.CharField('Staff Name:', max_length=255)
    
    #Profile
    profile = models.CharField(max_length=1024, blank=True)
    
    #area/Industry
    industry = models.CharField('Industry', max_length=1024, blank=True)
    where_going_destination = models.CharField('Location:', max_length=1024, blank=True)
    
    #Resources/Safety
    vulnerability_afraid_of_host = models.BooleanField('Afraid of host/employer/recruiter', default=False)
    vulnerability_doesnt_speak_destination_language = models.BooleanField("Doesn't speak language of destination", default=False)
    vulnerability_group_facebook = models.BooleanField('Facebook', default=False)
    vulnerability_group_missed_call = models.BooleanField('Missed Call', default=False)
    vulnerability_group_never_met_before = models.BooleanField('Meeting someone for the first time', default=False)
    vulnerability_group_other_website = models.CharField(max_length=127, blank=True)
    vulnerability_met_on_the_way = models.BooleanField('Met on their way', default=False)
    vulnerability_person_speaking_on_their_behalf = models.BooleanField('Person is not speaking on their own behalf / someone is speaking for them', default=False)
    vulnerability_refuses_family_info = models.BooleanField('Will not give family info', default=False).set_weight(35)
    vulnerability_supporting_documents_one_way_ticket = models.BooleanField('One way ticket', default=False)
    vulnerability_under_18_family_doesnt_know = models.BooleanField("Family doesn't know she is going to India", default=False).set_weight(45)
    vulnerability_insufficient_resource = models.BooleanField('insufficient resources_to live/get home', default=False)
    vulnerability_minor_without_guardian = models.BooleanField('Minor unaccompanied by guardian', default=False)
    vulnerability_family_unwilling = models.BooleanField('Family unwilling to let them go', default=False)
    vulnerability_first_time_traveling_abroad = models.BooleanField('First time traveling abroad', default=False)
    vulnerability_doesnt_speak_english = models.BooleanField("Doesn't speak English", default=False)
    vulnerability_non_relative_paid_flight = models.BooleanField('Non-relative paid for flight', default=False)
    vulnerability_paid_flight_in_cash = models.BooleanField('Non-relative paid for flight', default=False)
    vulnerability_connection_host_unclear = models.BooleanField('Connection to host/suspect limited or unclear', default=False)
    vulnerability_doesnt_have_required_visa = models.BooleanField("Doesn't have required visa/docs", default=False)
    vulnerability_family_friend_arranged_travel = models.BooleanField("Friend/Family arranged travel/job/studies", default=False)
    vulnerability_where_going_doesnt_know = models.BooleanField("Doesn't know where they are going", default=False)
    vulnerability_meeting_someone_met_online = models.BooleanField("Going to meet someone they met online", default=False)
    vulnerability_travel_arranged_by_other = models.BooleanField("Transportation arranged by someone else", default=False)
    vulnerability_travel_met_recently = models.BooleanField("Is or was traveling with someone they met recently", default=False)
    
    vulnerability_no_id = models.BooleanField("Does not have any form of ID", default=False)
    vulnerability_bus_driver_payment_at_destination = models.BooleanField("Bus driver expecting payment for travel at destination", default=False)
    vulnerability_first_time_traveling_to_city = models.BooleanField("Travelling to city from rural area for first time", default=False)
    vulnerability_no_mobile_phone = models.BooleanField("Does not own mobile phone", default=False)
    vulnerability_stranded_or_abandoned = models.BooleanField("Stranded/abandoned", default=False)
    vulnerability_different_last_name = models.BooleanField("Last name different from alleged relative", default=False)
    
    vulnerability_applied_job_doesnt_know_destination = models.BooleanField("Applied for job, but doesn't know destination", default=False)
    vulnerability_doesnt_speak_local_language = models.BooleanField("Doesn't speak local language", default=False)
    vulnerability_going_via_india = models.BooleanField("Going to a third country via India", default=False)
    vulnerability_cost_of_living_higher_than_wages = models.BooleanField("Cost of living in destination much higher than wages", default=False)
    vulnerability_doesnt_know_job_details = models.BooleanField("Doesn't know what job they are applying for", default=False)
    vulnerability_using_agent = models.BooleanField("Using an agent", default=False)
    vulnerability_mpa_excessive_time = models.BooleanField("MPA taking excessive time to process/send migrant", default=False)

    vulnerability_unregistered_agent = models.BooleanField("Using an unregistered agent", default=False)
    vulnerability_unregistered_agency = models.BooleanField("Using an unregistered recruitment agency", default=False)
    vulnerability_contract_against_law = models.BooleanField("Elements of contract are against the law", default=False)

    
    agreement_contract_language = models.BooleanField("Contract not in a language understood by the PV", default=False)
    agreement_mpa_not_bearing_cost = models.BooleanField("Company/MPA not bearing cost to Gulf/Malaysia", default=False)
    agreement_paid_agent = models.BooleanField("Paid money to agent", default=False)
    agreement_paid_above_standard = models.BooleanField("Paid more than government standard cost", default=False)
    agreement_no_receipt = models.BooleanField("No bhaar pai (receipt) for full amount of payment", default=False)
    
    preparation_unaware_of_process = models.BooleanField("Unaware of official employment migration process", default=False)
    preparation_did_not_complete = models.CharField(max_length=1024, blank=True)
    preparation_other = models.CharField(max_length=127, blank=True)
   
    evade_appearance_avoid_officials = models.BooleanField('Avoiding officials/hesitant to talk', default=False)
    evade_caught_in_lie = models.BooleanField('Caught in a lie or contradiction', default=False).set_weight(35)
    evade_couldnt_confirm_job = models.BooleanField('Could not confirm job', default=False).set_weight(10)
    evade_job_details_changed_en_route = models.BooleanField('Job details were changed en route', default=False)
    evade_no_bags_long_trip = models.BooleanField('No bags though claim to be going for a long time', default=False)
    evade_noticed_carrying_full_bags = models.BooleanField('Carrying Full bags', default=False)
    evade_signs_confirmed_deception = models.BooleanField('Called place and confirmed deception', default=False)
    evade_signs_fake_documentation = models.BooleanField('Fake documents', default=False)
    evade_signs_forged_false_documentation = models.BooleanField('Forged or falsified documents', default=False)
    evade_signs_other = models.CharField(max_length=127, blank=True)
    evade_signs_treatment = models.BooleanField('Treatment - no documentation / knowledge', default=False)
    evade_study_doesnt_know_school_details = models.BooleanField('Does not know details of school', default=False)
    evade_visa_misuse = models.BooleanField('Misuse - for purposes other than issued', default=False)
    
    #Control
    control_led_other_country = models.BooleanField('Led to other country without their knowledge', default=False)
    control_traveling_because_of_threat = models.BooleanField('Traveling because of a threat', default=False)
    control_owes_debt = models.BooleanField('Owes debt to person who recruited/paid travel', default=False)
    control_job = models.CharField(max_length=127, blank=True)
    control_promised_pay = models.CharField(max_length=127, blank=True)
    control_normal_pay = models.CharField(max_length=127, blank=True)
    control_promised_double = models.BooleanField('Promised pay more than double normal pay', default=False)
    control_promised_higher = models.BooleanField('Promised pay a little higher than normal pay', default=False)
    control_no_address_phone = models.BooleanField('No address / phone number (of job)', default=False)
    control_contradiction_stories = models.BooleanField('Contradiction between stories', default=False)
    control_drugged_or_drowsy = models.BooleanField('Girl appears drugged or drowsy', default=False)
    control_job_underqualified = models.BooleanField('Extremely underqualified for job', default=False)
    control_less_than_2_weeks_before_eloping = models.BooleanField('Less than 2 weeks before eloping', default=False)
    control_married_in_past_2_8_weeks = models.BooleanField('Married within the past 2-8 weeks', default=False).set_weight(10)
    control_married_in_past_2_weeks = models.BooleanField('Married in the past 2 weeks', default=False).set_weight(15)
    control_mobile_phone_taken_away = models.BooleanField('Their mobile phone was taken away', default=False)
    control_abducted = models.BooleanField('Abducted', default=False)
    control_not_real_job = models.BooleanField('Not a real job', default=False).set_weight(55)
    control_passport_with_broker = models.BooleanField('Passport is with a broker', default=False).set_weight(40)
    control_id_or_permit_with_broker = models.BooleanField('Passport is with a broker', default=False).set_weight(6)
    control_relationship_to_get_married = models.BooleanField('On their way to get married ', default=False)
    control_reported_total_red_flags = models.IntegerField('Reported Total Red Flag Points:', null=True, blank=True)
    control_status_known_trafficker = models.BooleanField('Is a known trafficker', default=False)
    control_connected_known_trafficker = models.BooleanField('Is connected to a known trafficker', default=False)
    control_traveling_with_someone_not_with_them = models.BooleanField('Was travelling with someone not with them', default=False)
    control_under_18_family_unwilling = models.BooleanField('Family unwilling to let her go', default=False).set_weight(60)
    control_where_going_someone_paid_expenses = models.BooleanField('Non relatives paid for their travel', default=False)
    control_wife_under_18 = models.BooleanField("Wife/fiancee is under 18", default=False)
    control_under_18_recruited_for_work = models.BooleanField("Under 18, recruited for work", default=False)
    control_under_16_recruited_for_work = models.BooleanField("Under 16, recruited for work", default=False)
    
    control_visa_misuse = models.BooleanField("Convinced by agent/MPA to work on visa other than work visa", default=False)
    control_facilitated_via_third_country = models.BooleanField("Process being fully facilitated by someone to travel to third country via India for work", default=False)
    control_women_enticed_unsave_area = models.BooleanField("Woman being enticed by agent/MPA to go for domestic work in Gulf/Malaysia", default=False)
    control_enticed_banned_area = models.BooleanField("Being enticed by agent/MPA to go to banned country for migrant worker", default=False)
    control_enticed_non_seasonal = models.BooleanField("Being enticed by MPA to go to South Korea or Israel for non-seasonal work", default=False)
    control_agreement_prepermission_mismatch = models.BooleanField("Job agreement and pre-permission details do not match", default=False)
    control_invalid_mpa = models.BooleanField("Using an invalid MPA", default=False)
    control_invalid_lt = models.BooleanField("No/invalid Lt number and/or demand letter", default=False)
    
    # SFE additional PV information
    pv_lt_number_before_counsel = models.CharField(max_length=127, blank=True)
    pv_lt_number_after_counsel = models.CharField(max_length=127, blank=True)
    pv_closest_contact = models.TextField(blank=True)
    
    mpa_agent_not_used = models.BooleanField("Check if PV did not use a MPA or agent", default=False)
    mpa_name = models.CharField(max_length=127, null=True, blank=True)
    mpa_phone = models.CharField(max_length=127, null=True, blank=True)
    mpa_who_initiated_contact = models.CharField(max_length=127, null=True,blank=True)
    mpa_how_contacted = models.CharField(max_length=127, null=True, blank=True)
    mpa_is_suspect = models.CharField(max_length=127, null=True,blank=True)
    
    agent_who_initiated_contact = models.CharField(max_length=127, null=True,blank=True)
    agent_how_contacted = models.CharField(max_length=127, null=True, blank=True)
    agent_is_suspect = models.CharField(max_length=127, null=True,blank=True)
    
    
    result_pv_tech_training = models.BooleanField("PV was referred to technical/vocational training", default=False)
    result_pv_other_education = models.BooleanField("PV was referred to other education", default=False)
    result_pv_changed_plans = models.CharField(max_length=127, null=True, blank=True)
    result_pv_local_job = models.BooleanField("PV decided to change plans and look for a job within Nepal due to SFE staff’s counseling", default=False)
    
    #Contact/Staff
    case_notes = models.TextField('Case Notes', blank=True)
    contact_paid = models.BooleanField(null=True)
    contact_paid_how_much = models.CharField('How much?', max_length=255, blank=True)
    rescue = models.BooleanField('Rescue', default=False)
    staff_who_noticed = models.CharField('Staff who noticed:', max_length=255, blank=True)
    talked_to_family_member = models.CharField(max_length=127, blank=True)
    which_contact = models.CharField(max_length=127, blank=True)
    who_noticed = models.CharField(max_length=127, null=True)
    
    #Reason
    call_subcommittee = models.BooleanField('Call Subcommittee Chairperson/Vice-Chairperson/Secretary', default=False)
    call_project_manager = models.BooleanField('Call Project Manager to confirm intercept', default=False)
    computed_total_red_flags = models.IntegerField('Computed Total Red Flag Points:', null=True, blank=True)
    convinced_by_staff = models.CharField(max_length=127, blank=True)
    convinced_by_family = models.CharField(max_length=127, blank=True)
    convinced_family_phone = models.CharField(max_length=127, blank=True)
    convinced_by_police = models.CharField(max_length=127, blank=True)
    pv_stopped_on_own = models.CharField(max_length=127, blank=True)
    evidence_categorization = models.CharField(max_length=127, null=True)
    has_signature = models.BooleanField('Scanned form has signature?', default=False)
    HOW_SURE_TRAFFICKING_CHOICES = [
        (1, '1 - Not at all sure'),
        (2, '2 - Unsure but suspects it'),
        (3, '3 - Somewhat sure'),
        (4, '4 - Very sure'),
        (5, '5 - Absolutely sure'),
    ]
    how_sure_was_trafficking = models.IntegerField('How sure are you that it was trafficking case?', choices=HOW_SURE_TRAFFICKING_CHOICES, null=True)
    immigration_lj_entry = models.CharField(max_length=127, null=True)
    immigration_lj_transit = models.CharField(max_length=127, null=True)
    immigration_lj_exit = models.CharField(max_length=127, null=True)
    immigration_entry = models.CharField(max_length=127, null=True)
    immigration_transit = models.CharField(max_length=127, null=True)
    immigration_exit = models.CharField(max_length=127, null=True)
    immigration_case_number = models.CharField(max_length=127, null=True)
    reason_for_intercept = models.TextField('Primary reason for intercept', blank=True)
    official_name = models.CharField(max_length=127, null=True)
    has_offical_signature = models.BooleanField('Has official signature', default=False)
    flight_number = models.CharField(max_length=127, null=True)
    route = models.TextField('Route', blank=True)

    
    # Compliance
    logbook_received = models.DateField(null=True)
    logbook_incomplete_questions = models.CharField(max_length=127, blank=True)
    logbook_incomplete_sections = models.CharField(max_length=127, blank=True)
    logbook_information_complete = models.DateField(null=True)
    logbook_notes = models.TextField('Logbook Notes', blank=True)
    logbook_submitted = models.DateField(null=True)
    
    #Verification
    logbook_first_verification = models.CharField(max_length=127, blank=True)
    logbook_first_reason = models.TextField('First Reason', blank=True)
    logbook_followup_call = models.CharField(max_length=127, blank=True)
    logbook_first_verification_date = models.DateField(null=True)
    logbook_first_verification_name = models.CharField(max_length=127, blank=True)
    verified_evidence_categorization = models.CharField(max_length=127, blank=True)
    logbook_second_reason = models.TextField('Second Reason', blank=True)
    verified_date = models.DateField(null=True)
    logbook_second_verification_name = models.CharField(max_length=127, blank=True)
    
    logbook_champion_verification = models.BooleanField('Champion verification', default=False)
    
    def get_key(self):
        return self.irf_number
    
    def get_form_type_name(self):
        return 'IRF'
    
    def get_form_date(self):
        return self.date_of_interception
    
    def to_str(self, value):
        if value is None:
            return 'None'
        else:
            return str(value)
    
    def __str__(self):
        return self.to_str(self.id) + ":" + self.to_str(self.irf_number) + ", " + self.to_str(self.number_of_victims) + ", " + self.to_str(self.location )+ ", " + self.to_str(self.number_of_traffickers) + ", " + self.to_str(self.staff_name)
    
    @staticmethod
    def key_field_name():
        return 'irf_number'
    
    @staticmethod
    def has_blind_verification(country):
        blind_verification_forms = FormCategory.objects.filter(name='Verification', category__category_type__name='card', form__form_type__name = 'IRF', form__stations__operating_country=country)
        return (len(blind_verification_forms) > 0)
        
    class Meta:
        indexes = [
            models.Index(fields=['logbook_submitted', 'station']),
            models.Index(fields=['logbook_first_verification_date', 'station']),
            models.Index(fields=['verified_date', 'station']),
        ]
    
class IntercepteeCommon(BaseCard):
    interception_record = models.ForeignKey(IrfCommon, related_name='interceptees', on_delete=models.CASCADE)
    relation_to = models.CharField(max_length=255, blank=True)
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.CASCADE)
    not_physically_present = models.CharField(max_length=127, blank=True)
    consent_to_use_photo = models.CharField(max_length=255, null=True)
    consent_to_use_information = models.CharField(max_length=255, null=True)

    def address1_as_string(self):
        rtn = ''
        try:
            rtn = self.person.address1
        except Exception:
            pass
        
        return rtn

    def address2_as_string(self):
        rtn = ''
        try:
            rtn = self.person.address2
        except Exception:
            pass
        
        return rtn
    
    def __str__(self):
        return "{} ({})".format(self.person.full_name, self.id)
    
    def set_parent(self, the_parent):
        self.interception_record = the_parent

class IrfAttachmentCommon(BaseCard):
    interception_record = models.ForeignKey(IrfCommon, on_delete=models.CASCADE)
    attachment_number = models.PositiveIntegerField(null=True, blank=True)
    description = models.CharField(max_length=126, null=True)
    attachment = models.FileField('Attach scanned copy of form (pdf or image)', upload_to='scanned_irf_forms')
    private_card = models.BooleanField(default=True)
    option = models.CharField(max_length=126, null=True)
    
    def set_parent(self, the_parent):
        self.interception_record = the_parent
        
    def is_private(self):
        return self.private_card

class IrfVerification(BaseCard):
    INITIAL = 1
    TIE_BREAK = 2
    TIE_BREAK_REVIEW = 3
    OVERRIDE = 4
    
    VERIFICATION_TYPE_CHOICES = [
        (INITIAL, 'Initial Verification'),
        (TIE_BREAK, 'Tie Break'),
        (TIE_BREAK_REVIEW, 'Tie Break Review'),
        (OVERRIDE, 'Override'),
    ]
    
    interception_record = models.ForeignKey(IrfCommon, on_delete=models.CASCADE)
    
    verification_type = models.IntegerField(VERIFICATION_TYPE_CHOICES)
    followup_call = models.CharField(max_length=127, blank=True)
    followup_details = models.TextField('followup details', blank=True)
    
    evidence_categorization = models.CharField(max_length=127)
    reason = models.TextField('reason', blank=True)
    verified_date = models.DateField()
    verifier = models.ForeignKey(Account, null=True, on_delete=models.SET_NULL)
    
    def set_parent(self, the_parent):
        self.interception_record = the_parent
    
    