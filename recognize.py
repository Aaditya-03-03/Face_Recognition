import cv2
import face_recognition
import numpy as np
from db import load_faces_db, log_attendance
from utils import face_distance, is_match

PROMPT_FOR_REGISTRATION = True  # Set to False to ignore unrecognized faces

def recognize_and_mark_attendance(metric='euclidean', threshold=0.6):
    faces = load_faces_db()
    if not faces:
        print('No enrolled faces found.')
        return
    known_embeddings = np.array([f['embedding'] for f in faces])
    user_ids = [f['user_id'] for f in faces]
    names = [f['name'] for f in faces]

    cap = cv2.VideoCapture(0)
    print('Press Q to quit.')
    while True:
        ret, frame = cap.read()
        if not ret:
            print('Failed to access webcam.')
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, boxes)
        for box, encoding in zip(boxes, encodings):
            distances = face_distance(known_embeddings, encoding, metric)
            idx, matched = is_match(distances, threshold)
            top, right, bottom, left = box
            if matched:
                user_id = user_ids[idx]
                name = names[idx]
                marked = log_attendance(user_id, name)
                label = f'{name} ({user_id})'
                if marked:
                    label += ' [Present]'
                else:
                    label += ' [Already marked]'
                color = (0,255,0)
            else:
                label = 'Unknown'
                color = (0,0,255)
                if PROMPT_FOR_REGISTRATION:
                    print('Unrecognized face detected. Prompting for registration...')
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.putText(frame, label, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.imshow('Attendance - Press Q to quit', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows() 