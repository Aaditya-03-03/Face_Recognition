import pickle
import os
import pandas as pd
from datetime import datetime

FACES_PKL = 'data/faces.pkl'
ATTENDANCE_CSV = 'data/attendance.csv'

def save_faces_db(faces):
    with open(FACES_PKL, 'wb') as f:
        pickle.dump(faces, f)

def load_faces_db():
    if not os.path.exists(FACES_PKL):
        return []
    with open(FACES_PKL, 'rb') as f:
        return pickle.load(f)

def log_attendance(user_id, name):
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')
    if not os.path.exists(ATTENDANCE_CSV):
        df = pd.DataFrame(columns=['user_id', 'name', 'date', 'time', 'status'])
    else:
        df = pd.read_csv(ATTENDANCE_CSV)
        # Add status column if missing (for backward compatibility)
        if 'status' not in df.columns:
            df['status'] = 'Present'
    # Only mark present once per day
    if not ((df['user_id'] == user_id) & (df['date'] == date_str)).any():
        new_row = pd.DataFrame([{'user_id': user_id, 'name': name, 'date': date_str, 'time': time_str, 'status': 'Present'}])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(ATTENDANCE_CSV, index=False)
        return True
    return False

def get_attendance_df():
    if not os.path.exists(ATTENDANCE_CSV):
        return pd.DataFrame(columns=['user_id', 'name', 'date', 'time', 'status'])
    df = pd.read_csv(ATTENDANCE_CSV)
    if 'status' not in df.columns:
        df['status'] = 'Present'
    return df 