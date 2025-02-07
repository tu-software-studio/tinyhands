import pandas as pd
import numpy as np
from io import BytesIO
from PIL import Image
import face_recognition
from urllib.parse import quote
import base64

from django.conf import settings
from django.core.cache import cache

from .models import MatchingPerson, FaceEncoding
from . import helper_analysis


QS_TO_DF_MAPPING = {"person": "person_id", "person__person__master_person": "master_person_id", "person__interception_record__station__operating_country__name": "country", "person__person__full_name": "full_name", "person__person__role": "role", "person__person__photo": "photo",
                    "person__person__gender": "gender", "person__person__age": "age", "person__interception_record__irf_number": "irf_number", "person__interception_record__date_time_entered_into_system": "date_time_entered_into_system", "face_encoding": "face_encoding", "outcome": "outcome"}

# Extract parameters from submitted form
def handle_select_params(data):
    params = {}
    params['country'] = data.getlist('country')
    params['role'] = data.getlist('role')
    params['gender'] = data.getlist('gender')
    return params


def queryset_to_dataframe(qs):
    rows = list(qs.values_list(*(list(QS_TO_DF_MAPPING.keys()))))
    return pd.DataFrame(rows, columns=list(QS_TO_DF_MAPPING.values()))


# Get dataframe of matching records based on params
def get_matching_records(params):
    countries = params.get('country')
    roles = params.get('role')
    genders = params.get('gender')

    qs = FaceEncoding.objects.select_related("person__interception_record")

    # If the "All" option is in the list of parameters, skip filtering
    if "All" not in countries:
        qs = qs.filter(
            person__interception_record__station__operating_country__name__in=countries)

    if "All" not in roles:
        qs = qs.filter(person__person__role__in=roles)

    if "All" not in genders:
        qs = qs.filter(person__person__gender__in=genders)

    qs = qs.filter(person__person__photo__isnull=False).filter(
        outcome__exact="encoded")
    df = queryset_to_dataframe(qs)

    return df


def to_data_uri(image_pil):
    data = BytesIO()
    image_pil.save(data, "JPEG")  # pick your format
    data64 = base64.b64encode(data.getvalue())
    return u'data:img/jpeg;base64,'+data64.decode('utf-8')

def uri_data_image(image_uri):
    image = base64.b64decode(image_uri)
    return image


def image_summary(image):
    face_landmarks, face_region = helper_analysis.face_landmarks_regions(image)
    sharpness_quality, sharpness_quality_label = helper_analysis.get_sharpness_quality(
        face_region)
    lighting_quality, lighting_quality_label = helper_analysis.get_lighting_quality(
        face_region)
    face_position_quality, face_position_quality_label = helper_analysis.get_face_position_quality(
        face_landmarks
    )
    occlusion_quality, occlusion_quality_label = helper_analysis.get_occlusion_quality(
        face_landmarks)
    resolution_quality, resolution_quality_label = helper_analysis.get_resolution_quality(
        face_region)

    narrative = f"The image has a {sharpness_quality_label} face. "

    if lighting_quality_label == "Flat Lighting":
        narrative += f"It appears somewhat uniformly lit, lacking depth due to {lighting_quality_label}. "
    else:
        narrative += f"It exhibits {lighting_quality_label}. "

    if face_position_quality_label == "Frontal Face":
        narrative += f"The subject is facing the camera directly, providing a {face_position_quality_label}. "
    elif face_position_quality_label == "Slightly Tilted Face":
        narrative += f"The subject's face is slightly tilted, but mostly frontal. "
    else:
        narrative += f"The face seems to be at an angle, showing a {face_position_quality_label}. "

    if occlusion_quality_label == "Clear Face":
        narrative += f"There aren't any significant obstructions, resulting in a {occlusion_quality_label}. "
    else:
        narrative += f"There are elements obscuring the facial features, indicating a {occlusion_quality_label}. "

    narrative += f"Lastly, we can describe it as a {resolution_quality_label} image."

    return narrative


def get_face(image_np):
    try:
        # Get face landmarks and face region
        face_landmarks, face_region = helper_analysis.face_landmarks_regions(
            image_np)

        # Ensure there are face landmarks detected
        if not face_landmarks:
            return

        # Extract bounding box of the detected face directly from face_landmarks_regions
        # face_location = face_recognition.face_locations(image_np, model="hog")[0]
        # top, right, bottom, left = face_location

        # Draw a red rectangle around the detected face on the original image
        # draw = ImageDraw.Draw(image_pil)

        # draw.rectangle(((left, top), (right, bottom)), outline="red", width=3)

    except Exception as e:
        return

    # Convert face region numpy array to PIL Image
    face_image_pil = Image.fromarray(face_region)

    return face_image_pil

# query for an image not by URL, but by...
def get_image(safe_url):
        person_image = person_np = person_image_array = None
        url = settings.MEDIA_ROOT + '/' + safe_url
        try:
            with open(url, "rb") as image_file:
                person_image = Image.open(image_file)
                person_np = face_recognition.load_image_file(image_file)
                person_image_array = np.array(person_image)
        except FileNotFoundError:
            print('Error finding the photo:', safe_url)
            # TODO: handle image not found
            raise
        except Exception as error:
            print(error)
            raise

        return person_image_array, person_np


def get_photo_and_encoding(selected_person):
    """
    Retrieves the photo URL and face encoding for a given person.

    Args:
        selected_person (str/int): The ID of the person for whom to retrieve the photo and encoding.

    Returns:
        tuple: A tuple containing the photo_url and the face encoding.
              Returns (None, None) if the person is not found.
    """
    try:
        matching_records = cache.get('matching_records')
        filtered_photos = matching_records[
            matching_records.person_id == int(selected_person)
        ].photo
        filtered_encoding = matching_records[
            matching_records.person_id == int(selected_person)
        ].face_encoding

        # Check if the person was found and data is available
        if not filtered_photos.empty and not filtered_encoding.empty:
            given_encoding = np.array(filtered_encoding.iloc[0])
            raw_url = filtered_photos.iloc[0]

            return raw_url, given_encoding
        else:
            print(f"No data found for person ID: {selected_person}")
            return None, None

    except Exception as e:
        print(
            f"An error occurred while retrieving data for person ID {selected_person}: {e}"
        )
        return None, None


def retrieve_photo_and_encoding(selected_person):
    """Retrieve photo URL and encoding for a given person."""
    selected_photo_url, given_encoding = get_photo_and_encoding(
        selected_person)
    if selected_photo_url and given_encoding is not None and given_encoding.size > 0:
        safe_url = quote(selected_photo_url, safe=":/")
        selected_person_image, selected_person_np = get_image(safe_url)
        selected_person_pil_image = Image.fromarray(
            selected_person_image.astype("uint8")
        )
        return given_encoding, selected_person_pil_image, selected_person_np
    return None, None, None


def get_closest_face_matches(encoding, limit):
    """
    Retrieves the closest face matches and their distances for a given face encoding.

    Args:
        encoding (array): The face encoding of the person to be matched.

    Returns:
        tuple: A tuple containing the IDs of the closest matches, the corresponding distances, and photo URLs.
              Returns (None, None, None) if no match is found or an error occurs.
    """
    try:
        matching_records = cache.get('matching_records')
        # print(matching_records[:10])

        known_encodings = np.array(
            matching_records["face_encoding"].tolist()
        )

        known_labels = matching_records["person_id"].tolist()

        # Calculate face distances
        face_distances = face_recognition.face_distance(
            known_encodings, encoding
        )

        # Find the indices of the matches sorted by distance
        sorted_indices = np.argsort(face_distances)

        # Sort known labels and distances using sorted_indices
        sorted_labels = [known_labels[i] for i in sorted_indices]
        sorted_distances = [face_distances[i] for i in sorted_indices]

        # Get photo URLs for sorted labels
        sorted_photo_urls = [
            matching_records[
                matching_records.person_id == int(label)
            ].photo.iloc[0]
            for label in sorted_labels
        ]

        print(sorted_labels[:10])

        upper_bound = min(limit, len(sorted_labels))
        return (
            sorted_labels[1:upper_bound],
            sorted_distances[1:upper_bound],
            sorted_photo_urls[1:upper_bound],
        )

    except Exception as e:
        print(f"An error occurred while finding the closest face matches: {e}")
        return None, None, None


# # Run analysis on selected record and display results
# def get_image_formats_from_records(selected_person):
#     """Handle the 'Select from records' choice and return the encoding and image."""
#     # Initialize default return values
#     (given_encoding, selected_person_pil_image,
#      selected_person_np) = (None, None, None)

#     try:
#         (
#             given_encoding,
#             selected_person_pil_image,
#             selected_person_np,
#         ) = retrieve_photo_and_encoding(selected_person)
#     except Exception as e:
#         print(
#             f"Error processing the selected_person {selected_person}: {str(e)}"
#         )

#     return (
#         given_encoding,
#         selected_person_pil_image,
#         selected_person_np,
#     )


def get_display_data(image_pil, image_np):
    """Display the image and its face rectangle in the given column.
    :param summary:
    """

    face_image_pil = get_face(image_np)

    if face_image_pil is None:
        print("Failed to get image details from get_face.")
        return

    image_summary_text = image_summary(image_np)

    image_uri = to_data_uri(image_pil)
    face_image_uri = to_data_uri(face_image_pil)

    return (image_uri, face_image_uri, image_summary_text)


# # TODO: selected_person_image == image_pil
def get_selected_person_display_data(selected_person):
    (
        given_encoding,
        selected_person_pil_image,
        selected_person_np,
    ) = get_image_formats_from_records(selected_person)

    # NOTE: selected_person_np could be being overwritten...
    # Could there be a pil without np?
    # selected_person_np = np.array(selected_person_pil_image)
    selected_person_details = helper_analysis.get_person_details(
        int(selected_person))

    (image_uri, summary, face_image_uri, image_summary_text) = get_display_data(
        selected_person_pil_image,
        selected_person_np,
    )

    return image_uri, summary, face_image_uri, image_summary_text, given_encoding, selected_person_details


# List of tuples of context to be displayed for each record identified as a match
# Return a list of instances of MatchingPerson for each record identified as a match
def get_matches_display_data(given_encoding, limit):
    matches = []
    closest_matches, face_distances, closest_photo_urls = get_closest_face_matches(
        given_encoding, limit
    )

    for (closest_match_person_id, face_distance, closest_photo_url) in zip(closest_matches, face_distances, closest_photo_urls):
        print(closest_match_person_id, face_distance, closest_photo_url)
        safe_url = quote(closest_photo_url, safe=":/")

        # Get actual image from url
        match_person_image, match_person_np = get_image(safe_url)

        match_person_pil_image = Image.fromarray(
            match_person_image.astype("uint8"))

        # Get details related to matching person
        details = helper_analysis.get_person_details(
            closest_match_person_id)
        
        details = details[0]

        # Get processed full image, face image, and analysis
        # TODO: consider computing face image client side to reduce package size
        (full_image_uri, face_image_uri, face_analysis) = get_display_data(
            match_person_pil_image,
            match_person_np,
        )

        matches.append(
            MatchingPerson(full_name=details['full_name'], person_id=closest_match_person_id, gender=details['gender'], role=details['role'], face_photo=face_image_uri, full_photo=full_image_uri, irf_number=details['irf_number'], nationality=details['country'], age_at_interception=str(details['age']), date_of_interception=str(details['date_time_entered_into_system']), face_analysis=face_analysis, face_distance=face_distance)
        )

    return matches


def display_selected_and_closest_match_images(
    given_encoding, selected_person, selected_person_image
):
    """Display the selected image and its closest match."""
    print("--\t-- display_selected_and_closest_match_image()")

    # handle_voting(user_id, selected_person, closest_match)


def handle_params_form_submission(request):
    context = {}
    request.session['submitted-params'] = request.GET

    # Show previous selections
    context['params_form'] = helper_forms.params_form(request)

    # TODO: if form.is_valid():
    params = handle_select_params(request.GET)

    # Filter for records based on given parameters
    matching_records = get_matching_records(params)
    cache.set('matching_records', matching_records)

    # Count matching records
    num_matching_records = len(matching_records)
    context['num_matching_records'] = num_matching_records

    # Get list of IRFs from matching records
    irfs = list(matching_records['irf_number'].sort_values().drop_duplicates())
    request.session['irfs'] = irfs

    # Display empty form
    context['irf_form'] = helper_forms.irf_form(request, initial=True)
    return request, context


def handle_irf_form_submission(request):
    context = {}
    request.session['submitted-irf'] = request.GET

    # Show previous selections
    context['params_form'] = helper_forms.params_form(request)
    context['irf_form'] = helper_forms.irf_form(request)

    # Display empty form
    context['person_form'] = helper_forms.person_form(request, initial=True)
    return request, context


def handle_person_form_submission(request):
    # TODO: auto submit if there is only one person_id
    context = {}

    # Show previous selections
    context['params_form'] = helper_forms.params_form(request)
    context['irf_form'] = helper_forms.irf_form(request)
    request.session['submitted-person'] = request.GET
    context['person_form'] = helper_forms.person_form(request)

    selected_person = request.GET.get('person')
    context['selected_person'] = selected_person

    # Get encoding and other data for selected person
    (image_uri, summary, face_image_uri, image_summary_text,
     given_encoding) = get_selected_person_display_data(selected_person)

    context['selected_image_uri'] = image_uri
    context['selected_summary'] = summary
    context['selected_face_image_uri'] = face_image_uri
    context['selected_image_summary_text'] = image_summary_text

    # if given_encoding is not None and given_encoding.size > 0 and selected_person_image:
    # context['facematcher_form'] = helper.facematcher_form()
    # TODO: Remove me
    limit = 5

    # Get encoding and other data for matches to selected person
    matches = get_matches_display_data(given_encoding, limit)
    context['matches'] = matches

    # helper.display_selected_and_closest_match_images(
    #     given_encoding, selected_person, selected_person_image
    # )

    # TODO: Figure out how to render images in template
    return request, context


# # Run function manually to refresh list of roles to filter by
# # Roles are queried from DataentryPerson roles, parsed by semicolon, normalized by case.
# # Remove roles iwth more than one space
# # Search for "suspect" or "Suspect" should match roles of "SUSPECT", "suspect", "Broker; suspect", etc
# # NOTE: Potential matches that have roles spelled incorrectly or roles that are only used once will be omitted
# #TODO: Call somewhere
# def generate_roles():
#     # list of roles
#     initial_roles = DataentryPerson.objects.values_list('role', flat=True).distinct()
#     initial_roles = [r.lower() for r in initial_roles if r]
#     roles = []

#     # Parse roles by semicolon
#     for item in initial_roles:
#         split_item = item.split(';')
#         for role in split_item:
#             if role not in roles and role.count(' ') < 2:
#                 roles.append(role)

#     return roles.sort()
