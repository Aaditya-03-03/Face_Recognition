import cv2
import face_recognition
import numpy as np
from db import load_faces_db, save_faces_db


def enroll_face():
    cap = cv2.VideoCapture(0)
    print('Press SPACE to capture your face.')
    while True:
        ret, frame = cap.read()
        if not ret:
            print('Failed to access webcam.')
            break
        cv2.imshow('Enroll - Press SPACE to capture', frame)
        if cv2.waitKey(1) & 0xFF == ord(' '):
            break
    cap.release()
    cv2.destroyAllWindows()

    # Detect face
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    boxes = face_recognition.face_locations(rgb)
    if not boxes:
        print('No face detected. Try again.')
        return
    encoding = face_recognition.face_encodings(rgb, boxes)[0]

    user_id = input('Enter unique ID: ')
    name = input('Enter name: ')

    faces = load_faces_db()
    faces.append({'user_id': user_id, 'name': name, 'embedding': encoding})
    save_faces_db(faces)
    print(f'Enrolled {name} ({user_id}) successfully.') 