from django.db import models
from django.db.models import JSONField
from .person import Person
from .form import BaseCard
from .form import BaseForm
from .incident import Incident

class Suspect(BaseForm):
    # Top
    sf_number = models.CharField(max_length=20, unique=True)
    
    # Other incidents that might be associated with this suspect
    associated_incidents = models.ManyToManyField(Incident, related_name='associated_incidents')
    
    # Incidents with which this suspect is known to be involved
    # Initially only one Incident
    incidents = models.ManyToManyField(Incident)
    
    # Merged version of suspect information cards
    # in main form so that list can access for ordering/filtering
    merged_person = models.ForeignKey(Person, null=True, on_delete=models.CASCADE)
    merged_vehicle = models.CharField(max_length=126, null=True)
    merged_plate_number = models.CharField(max_length=126, null=True)
    # merged_location_where_spend_time added for 2024_09
    merged_location_where_spend_time = models.CharField(max_length=126, blank=True, null=True)
    
    # Logbook
    logbook_received = models.DateField(null=True)
    logbook_incomplete_questions = models.CharField(max_length=127, blank=True)
    logbook_incomplete_sections = models.CharField(max_length=127, blank=True)
    logbook_information_complete = models.DateField(null=True)
    logbook_notes = models.TextField('Logbook Notes', blank=True)
    logbook_submitted = models.DateField(null=True)
    
    def get_key(self):
        return self.sf_number
    
    def get_form_type_name(self):
        return 'SF'
    
    def get_form_date(self):
        return self.date_time_last_updated.date()
    
    @staticmethod
    def key_field_name():
        return 'sf_number'
    
    def get_common_master_person(self):
        # cannot directly reference SuspectInformation as it is declared later
        mod = __import__('dataentry.models.suspect', fromlist=['SuspectInformation'])
        form_model = getattr(mod, 'SuspectInformation')
        suspect_infos = form_model.objects.filter(suspect=self)
        
        if len(suspect_infos) > 0:
            common_master_person = suspect_infos[0].person.master_person
        else:
            common_master_person = None
        
        return common_master_person
    
"""
    Card for each source
"""
class SuspectInformation(BaseCard):
    suspect = models.ForeignKey(Suspect, on_delete=models.CASCADE)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, null=True)
    source_type = models.CharField(max_length=126, null=True)
    source_title = models.CharField(max_length=126, blank=True)
    interviewer_name = models.CharField(max_length=126, blank=True)
    interview_date = models.DateField(null=True, default=None)
    # location is no longer used in 2024_09
    location = models.CharField(max_length=255, blank=True, null=True)
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.CASCADE)
    vehicle = models.CharField(max_length=126, null=True)
    plate_number = models.CharField(max_length=126, null=True)
    # fields added for 2040_09
    location_where_spend_time = models.CharField(max_length=126, blank=True, null=True)
    source_contact_info = models.CharField(max_length=126, blank=True, null=True)
    
    def set_parent(self, the_parent):
        self.suspect = the_parent

"""
    Initially there will only be one SuspectAssociation card for the
    incident.  In the future, we may merge suspects which would result
    in data from multiple incidents in the same suspect form.
"""        
class SuspectAssociation(BaseCard):
    suspect = models.ForeignKey(Suspect, on_delete=models.CASCADE)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    associated_pvs = models.TextField(null=True)
    associated_suspects = models.TextField(null=True)
    # associated_locations no longer used in 2024_09
    associated_locations = models.TextField(null=True)
    narrative = models.TextField('Narrative', blank=True)
    # fields added for 2040_09
    previous_legal_actions = models.TextField('Previous Legal Actions', blank=True)
    
    def set_parent(self, the_parent):
        self.suspect = the_parent
    
"""
     Card for each person who evaluates the suspect
"""   
class SuspectEvaluation(BaseCard):
    suspect = models.ForeignKey(Suspect, on_delete=models.CASCADE)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    evaluator_type = models.CharField(max_length=126, null=True)
    evaluator_name = models.CharField(max_length=126, null=True)
    evaluation = models.CharField(max_length=126, null=True)
    
    def set_parent(self, the_parent):
        self.suspect = the_parent

"""
    Initially there will only be one SuspectLegal card for the
    incident.  In the future, we may merge suspects which would result
    in data from multiple incidents in the same suspect form.
"""   
class SuspectLegal(BaseCard):
    suspect = models.ForeignKey(Suspect, on_delete=models.CASCADE)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    arrested = models.CharField(max_length=126, null=True)
    arrest_date = models.DateField(null=True, default=None)
    police_case = models.CharField(max_length=126, null=True)
    charge_sheet_date = models.DateField(null=True, default=None)
    crimes_charged = models.TextField('Crimes Charged', blank=True)
    # pv_attempt and pv_unable fields info moved to SuspectLegalPv for 2024_09
    pv_attempt = models.CharField(max_length=126, null=True)
    pv_unable = models.CharField(max_length=126, null=True)
    location_attempt = models.CharField(max_length=126, null=True)
    # location_unable field unused for 2024_09
    location_unable = models.CharField(max_length=126, null=True)
    location_last_address = JSONField(null=True)
    location_last_latitude = models.FloatField(null=True)
    location_last_longitude = models.FloatField(null=True)
    location_last_address_notes = models.TextField('Address Notes', blank=True)
    location_last_date = models.DateField(null=True, default=None)
    police_attempt = models.CharField(max_length=126, null=True)
    # police_unable field unused for 2024_09
    police_unable = models.CharField(max_length=126, null=True)
    # Fields added for 2024_09
    anything_cause_pvs_to_file = models.TextField(null=True)
    police_contact = models.CharField(max_length=126, null=True)
    what_needed_for_arrest = models.TextField(null=True)
    
    def set_parent(self, the_parent):
        self.suspect = the_parent


class SuspectLegalPv(BaseCard):
    suspect = models.ForeignKey(Suspect, on_delete=models.CASCADE)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    pv_name = models.CharField(max_length=126, null=True)
    willing_to_file = models.TextField(null=True)
    hesitation_concern = models.TextField(null=True)

    def set_parent(self, the_parent):
        self.suspect = the_parent


"""
    Card for each attachment to the suspect form
"""  
class SuspectAttachment(BaseCard):
    suspect = models.ForeignKey(Suspect, on_delete=models.CASCADE)
    attachment_number = models.PositiveIntegerField(null=True, blank=True)
    description = models.CharField(max_length=126, null=True)
    attachment = models.FileField('Attach scanned copy of form (pdf or image)', upload_to='sf_attachments')
    private_card = models.BooleanField(default=True)
    option = models.CharField(max_length=126, null=True)
    
    def set_parent(self, the_parent):
        self.suspect = the_parent
        
    def is_private(self):
        return self.private_card