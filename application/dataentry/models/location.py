from django.db import models
from django.db.models import JSONField
from .form import BaseCard
from .form import BaseForm
from .incident import Incident

class LocationForm(BaseForm):
    # Top
    lf_number = models.CharField(max_length=20, unique=True)
    
    # Other incidents that might be associated with this suspect
    associated_incidents = models.ManyToManyField(Incident, related_name='location_associated_incidents')
    
    # Incidents with which this suspect is known to be involved
    # Initially only one Incident
    incidents = models.ManyToManyField(Incident)
    
    merged_place = models.CharField(max_length=126, null=True)
    merged_place_detail = models.CharField(max_length=126, null=True)
    merged_place_kind = models.CharField(max_length=126, null=True)
    merged_address = JSONField(null=True)
    merged_latitude = models.FloatField(null=True)
    merged_longitude = models.FloatField(null=True)
    merged_phone = models.CharField(max_length=126, null=True)
    merged_name_signboard = models.CharField(max_length=126, null=True)
    merged_location_in_town = models.CharField(max_length=126, null=True)
    merged_color = models.CharField(max_length=126, null=True)
    merged_number_of_levels = models.CharField(max_length=126, null=True)
    merged_description = models.TextField('Descriptive Features', blank=True) # address notes
    merged_nearby_landmarks = models.CharField(max_length=126, null=True)
    
    evidence = models.TextField(blank=True)
    how_facilitate = models.TextField(blank=True)
    
    #Logbook
    logbook_received = models.DateField(null=True)
    logbook_incomplete_questions = models.CharField(max_length=127, blank=True)
    logbook_incomplete_sections = models.CharField(max_length=127, blank=True)
    logbook_information_complete = models.DateField(null=True)
    logbook_notes = models.TextField('Logbook Notes', blank=True)
    logbook_submitted = models.DateField(null=True)
    
    def get_key(self):
        return self.lf_number
    
    def get_form_type_name(self):
        return 'LF'
    
    def get_form_date(self):
        return self.date_time_last_updated.date()
    
    @staticmethod
    def key_field_name():
        return 'lf_number'
    
class LocationInformation(BaseCard):
    lf = models.ForeignKey(LocationForm, on_delete=models.CASCADE)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, null=True)
    source_type = models.CharField(max_length=126, null=True)
    source_title = models.CharField(max_length=126, blank=True)
    source_contact_info = models.CharField(max_length=126, blank=True, null=True)
    interviewer_name = models.CharField(max_length=126, blank=True)
    interview_date = models.DateField(null=True, default=None)
    location = models.CharField(max_length=255, blank=True, null=True)
    place = models.CharField(max_length=126, null=True)
    place_detail = models.CharField(max_length=126, null=True)
    place_kind = models.CharField(max_length=126, null=True)
    recruitment_agency_name = models.CharField(max_length=126, null=True)
    address = JSONField(null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    phone = models.CharField(max_length=126, null=True)
    name_signboard = models.CharField(max_length=126, null=True)
    location_in_town = models.CharField(max_length=126, null=True)
    color = models.CharField(max_length=126, null=True)
    number_of_levels = models.CharField(max_length=126, null=True)
    description = models.TextField('Descriptive Features', blank=True) # address notes
    nearby_landmarks = models.CharField(max_length=126, null=True)
    
    persons_in_charge = models.CharField(max_length=126, null=True)
    pvs_visited = models.TextField(null=True)
    stay_how_long = models.CharField(max_length=126, null=True)
    start_date = models.DateField(null=True, default=None)
    attempt_hide = models.CharField(max_length=126, null=True)
    attempt_explanation = models.CharField(max_length=126, null=True)
    free_to_go = models.CharField(max_length=126, null=True)
    free_to_go_explanation = models.CharField(max_length=126, null=True)
    suspects_associative = models.TextField(null=True)
    
    def set_parent(self, the_parent):
        self.lf = the_parent

# LocationAssociation no longer used information added to LocationInformation
class LocationAssociation(BaseCard):
    lf = models.ForeignKey(LocationForm, on_delete=models.CASCADE)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, null=True)
    source_type = models.CharField(max_length=126, null=True)
    source_title = models.CharField(max_length=126, blank=True)
    interviewer_name = models.CharField(max_length=126, blank=True)
    interview_date = models.DateField(null=True, default=None)
    location = models.CharField(max_length=255, blank=True)    
    persons_in_charge = models.TextField(null=True)
    pvs_visited = models.TextField(null=True)
    stay_how_long = models.CharField(max_length=126, null=True)
    start_date = models.DateField(null=True, default=None)
    attempt_hide = models.CharField(max_length=126, null=True)
    attempt_explanation = models.CharField(max_length=126, null=True)
    free_to_go = models.CharField(max_length=126, null=True)
    free_to_go_explanation = models.CharField(max_length=126, null=True)
    suspects_associative = models.TextField(null=True)
    
    def set_parent(self, the_parent):
        self.lf = the_parent
    
class LocationEvaluation(BaseCard):
    lf = models.ForeignKey(LocationForm, on_delete=models.CASCADE)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    evaluator_type = models.CharField(max_length=126, null=True)
    evaluator_name = models.CharField(max_length=126, null=True)
    evaluation = models.CharField(max_length=126, null=True)
    
    def set_parent(self, the_parent):
        self.lf = the_parent

class LocationAttachment(BaseCard):
    lf = models.ForeignKey(LocationForm, on_delete=models.CASCADE)
    attachment_number = models.PositiveIntegerField(null=True, blank=True)
    description = models.CharField(max_length=126, null=True)
    attachment = models.FileField('Attach scanned copy of form (pdf or image)', upload_to='lf_attachments')
    private_card = models.BooleanField(default=True)
    option = models.CharField(max_length=126, null=True)
    
    def set_parent(self, the_parent):
        self.lf = the_parent
        
    def is_private(self):
        return self.private_card