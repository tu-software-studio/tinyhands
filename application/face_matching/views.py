import json
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from django.core.cache import cache

from . import helper, helper_upload_photo

from .serializers import MatchingDataSerializer
from .models import AnalyzedPerson, MatchingData


class FaceMatchingViewSet(viewsets.ModelViewSet):
    serializer_class = MatchingDataSerializer
    permission_classes = [IsAuthenticated]
    permissions_required = []
    parser_classes = [MultiPartParser, FormParser]

    # call functions to encode given image
    # find matching faces in database
    # return display data
    @action(detail=False, methods=['post'])
    def get_upload_matches(self, request):
        print("\n\nget_upload_matches() called")
        if request.POST:
            params = request.data.get("params")
            file = request.FILES.get("file")
            # convert params from string to JSON
            params = params.replace('\\"', '"')
            params = json.loads(params)

            # 1. Get matching records for given parameters
            matching_records = helper.get_matching_records(params)
            cache.set('matching_records', matching_records)

            # 2. Get encodings and other data for given image
            # TODO: handle case where uploaded image does not have a face
            (given_encoding, selected_person_image, selected_person_np) = helper_upload_photo.get_image_formats_from_file(file)

            # 3. Get face_photo and analysis, in addition to full_photo for analyzed person
            (image_uri, face_image_uri, image_summary_text) = helper.get_display_data(selected_person_image, selected_person_np)

            # 4. Package analyzedPerson
            analyzedPerson = AnalyzedPerson(full_photo=file, face_photo=face_image_uri, face_analysis=image_summary_text)

            # 5. Get X matches with the given image encoding
            # TODO: Make limit dynamic
            matchingPersons = helper.get_matches_display_data(given_encoding, limit=5)

            # 6. Package MatchingData
            # TODO: check if data types match
            matchingData = MatchingData(analyzedPerson, matchingPersons)

            # TODO: write serializer
            serializer = self.get_serializer(matchingData, many=True)
            json_data = json.dumps(matchingData, default=lambda matchingData: matchingData.__dict__)
            return Response(json_data, status=status.HTTP_201_CREATED)

            # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        else:
            # TODO: Handle if no request.body
            print("Error receiving uploaded image.")
