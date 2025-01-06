import cv2
import numpy as np
import face_recognition

from django.core.cache import cache


# Constants
gender_mapping = {"M": "male", "F": "female"}

role_mapping = {
    "PVOT": "victim",
    "Broker": "broker",
    "Companion": "companion",
    "Suspect": "suspect",
}


def get_sharpness_quality(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    variance_of_laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()

    if variance_of_laplacian < 50:
        return 1, "Blurry"
    elif variance_of_laplacian < 100:
        return 2, "Moderately Sharp"
    else:
        return 3, "Sharp"


def get_lighting_quality(face_region):
    mean = np.mean(face_region)
    std = np.std(face_region)

    if mean < 50 or mean > 205:
        return 1, "Poor Lighting"
    elif std < 50:
        return 1, "Flat Lighting"
    else:
        return 3, "Good Lighting"


def get_face_position_quality(face_landmarks):
    if not face_landmarks:
        return 0, "No Face Detected"

    # Just using the first face for this example
    landmarks = face_landmarks[0]

    left_eye = np.array(landmarks["left_eye"])
    right_eye = np.array(landmarks["right_eye"])

    left_eye_center = left_eye.mean(axis=0)
    right_eye_center = right_eye.mean(axis=0)

    dx = right_eye_center[0] - left_eye_center[0]
    dy = right_eye_center[1] - left_eye_center[1]

    angle = np.arctan2(dy, dx) * 180 / np.pi

    if abs(angle) > 15:
        return 1, "Tilted Face"
    elif abs(angle) > 5:
        return 2, "Slightly Tilted Face"
    else:
        return 3, "Frontal Face"


def get_occlusion_quality(face_landmarks):
    # Assume the face landmarks for eyes and nose are crucial
    landmarks = face_landmarks[0]
    if (
        not landmarks["left_eye"]
        or not landmarks["right_eye"]
        or not landmarks["nose_tip"]
    ):
        return 1, "Significant Occlusion"
    else:
        return 3, "Clear Face"


def get_resolution_quality(face_region):
    height, width = face_region.shape[:2]

    if height * width < 60 * 80:  # Roughly passport photo size
        return 1, "Low Resolution"
    elif height * width < 120 * 160:  # Roughly twice the passport size
        return 2, "Medium Resolution"
    else:
        return 3, "High Resolution"


def get_similarity_description(face_distance):
    if face_distance <= 0.1:
        return "Appears identical"
    if face_distance <= 0.2:
        return "Almost identical"
    if face_distance <= 0.3:
        return "Highly Similar"
    elif face_distance <= 0.4:
        return "Very Similar"
    elif face_distance <= 0.5:
        return "Similar"
    elif face_distance <= 0.6:
        return "Moderately Similar"
    elif face_distance <= 0.7:
        return "Slightly Similar"

    else:
        return "Not Similar at all"


def face_landmarks_regions(image):
    face_locations = face_recognition.face_locations(image, model="hog")
    face_landmarks = face_recognition.face_landmarks(image, face_locations)
    face_location = face_locations[0]
    top, right, bottom, left = face_location
    face_region = image[top:bottom, left:right]
    return face_landmarks, face_region


def get_person_details(person_id):
    try:
        matching_records = cache.get('matching_records')
        person_details = matching_records.loc[
            matching_records["person_id"] == int(person_id), :
        ].to_dict(orient="records")

        if not person_details:
            return f"no data for {person_id}"
        
        return person_details
    except Exception as e:
        return f"an error occurred retrieving data for {person_id}"
