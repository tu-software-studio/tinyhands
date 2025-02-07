import face_recognition as fr
from .db_conn import DB_Conn
import numpy as np


def get_faces_distance(person1_encoding, person2_encoding):
    # Ensure the encodings are NumPy arrays
    person1_encoding_array = np.atleast_2d(np.asarray(person1_encoding))
    person2_encoding_array = np.asarray(person2_encoding)

    # Calculate the face distance using the face_recognition library
    distance = fr.face_distance(
        person2_encoding_array, person1_encoding_array
    )
    # Calculate match percentage
    return 100 * (1 - distance[0])


def get_face_encoding(person_id):
    # Define the SQL query with a placeholder for the parameter
    query = "SELECT face_encoding FROM public.face_encodings WHERE person_id = %s;"

    # Initialize the database connection using a context manager
    with DB_Conn() as dbc:
        # Execute the query with the parameter
        face_encoding_df = dbc.ex_query(query, (person_id,))

    # Check if the DataFrame is empty
    if not face_encoding_df.empty:
        # Retrieve the face encoding
        face_encoding = face_encoding_df.iloc[0]['face_encoding']
        # Check if the face_encoding is already in the list format
        if isinstance(face_encoding, list):
            # Convert the list to a NumPy array and return
            return np.array(face_encoding)
        else:
            # If it's not a list, it's an unexpected type. Handle as needed.
            raise TypeError("Face encoding is not a list.")
    else:
        # Return None if no record was found
        return None

def get_personids_facematch(person_id1, person_id2):
    person1_encoding = get_face_encoding(person_id1)
    person2_encoding = get_face_encoding(person_id2)
    if person1_encoding is not None and person2_encoding is not None:
        return get_faces_distance(person1_encoding, person2_encoding)
    else:
        return None




