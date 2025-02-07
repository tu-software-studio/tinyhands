from django.db import models
from django.contrib.postgres.fields import ArrayField
from dataentry.models import IntercepteeCommon

class AnalyzedPerson:
    def __init__(self, full_photo, face_photo=None, face_analysis=None):
        self.full_photo = full_photo
        self.face_photo = face_photo
        self.face_analysis = face_analysis


class MatchingPerson():
    def __init__(self, full_name, person_id, gender, role, face_photo, full_photo, irf_number, nationality, age_at_interception, date_of_interception, face_analysis, face_distance):
        self.full_name = full_name 
        self.person_id = person_id 
        self.gender = gender 
        self.role = role 
        self.irf_number = irf_number 
        self.nationality = nationality 
        self.age_at_interception = age_at_interception 
        self.date_of_interception = date_of_interception 
        self.face_analysis = face_analysis 
        self.face_distance = face_distance 
        self.face_photo = face_photo 
        self.full_photo = full_photo 


class MatchingData():
    def __init__(self, analyzedPerson, matchingPersons):
        self.analyzedPerson = analyzedPerson
        self.matchingPersons = matchingPersons


class FaceEncoding(models.Model):
    person = models.ForeignKey(IntercepteeCommon, primary_key=True,
                                  to_field="person_id", db_column="person_id", on_delete=models.DO_NOTHING)
    # person = models.IntegerField(primary_key=True)
    # This field type is a guess.
    face_encoding = ArrayField(models.FloatField(
        blank=True), blank=True, size=128)
    outcome = models.TextField(blank=True)

    class Meta:
        db_table = 'face_encodings'

        def __str__(self):
            return self.person_id

