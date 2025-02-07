from rest_framework import serializers
from .models import MatchingData, MatchingPerson, AnalyzedPerson
 
class AnalyzedPersonSerializer(serializers.Serializer):
    full_photo = serializers.ImageField()
    face_photo = serializers.ImageField()
    face_analysis = serializers.CharField()


class MatchingPersonSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, allow_null=True)
    person_id = serializers.CharField(max_length=6)
    gender = serializers.CharField(max_length=4)
    role = serializers.CharField(max_length=126, allow_null=True)
    face_photo = serializers.ImageField()
    full_photo = serializers.ImageField()
    irf_number = serializers.CharField(max_length=6)
    nationality = serializers.CharField(max_length=127, default='')
    age_at_interception = serializers.IntegerField(allow_null=True)
    date_of_interception = serializers.DateField('Interception date', allow_null=True, default=None)
    face_analysis = serializers.CharField()
    face_distance = serializers.DecimalField(max_digits=2, decimal_places=2)
  
    
class MatchingDataSerializer(serializers.Serializer):
    analyzedPerson = AnalyzedPersonSerializer()
    matchingPersons = MatchingPersonSerializer(many=True)
