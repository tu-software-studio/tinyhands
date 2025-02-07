import fitz
import numpy as np
from io import BytesIO
from PIL import Image
import face_recognition

from . import helper

def get_image_from_pdf(uploaded_file):
    # Open the PDF file
    pdf = fitz.open("pdf", uploaded_file.read())
    # Look for the first image in the PDF
    image_found = False
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = pdf.extract_image(xref)
            image_bytes = base_image["image"]
            selected_person_image = Image.open(BytesIO(image_bytes))
            selected_person_np = np.array(selected_person_image)
            face_locations = face_recognition.face_locations(
                selected_person_np, model="hog"
            )
            if face_locations:
                given_encoding = face_recognition.face_encodings(
                    selected_person_np, known_face_locations=face_locations
                )
                image_found = True
                break  # Only take the first image
        if image_found:
            break
    if not image_found:
        print(
            "No images found in the PDF. Please upload a PDF with images."
        )
        return

    return given_encoding, selected_person_image, selected_person_np, face_locations


def get_image_formats_from_file(uploaded_file):
    """
    Handle the 'Upload an image' choice, process the image,
    and return its encoding along with other related information.
    """

    print("get_image_formats_from_file()")

    # Initialize default return values
    given_encoding, selected_person_image, selected_person_np = None, None, None

    # TODO: Validate file extension

    if uploaded_file:
        try:
            if uploaded_file.content_type == 'application/pdf':
                given_encoding, selected_person_image, selected_person_np, face_locations = get_image_from_pdf(
                    uploaded_file)

            else:
                # It's an image file, not a PDF
                selected_person_image = Image.open(
                    uploaded_file).convert("RGB")
                selected_person_np = np.array(selected_person_image)
                face_locations = face_recognition.face_locations(
                    selected_person_np, model="hog"
                )

            # If an image is loaded, process it
            if selected_person_image:
                if face_locations:
                    encodings = face_recognition.face_encodings(
                        selected_person_np, known_face_locations=face_locations
                    )
                    if encodings:
                        given_encoding = encodings[0]
                else:
                    print(
                        "No face detected in the uploaded image. Please upload a different image."
                    )
        except Exception as e:  # Catch any other exceptions
            print(f"An error occurred: {e}")
    else:
        print(
                "No file uploaded."
            )
    return given_encoding, selected_person_image, selected_person_np
