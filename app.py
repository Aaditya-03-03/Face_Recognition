from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os
import base64
import cv2
import numpy as np
import face_recognition
from db import load_faces_db, save_faces_db
from enroll import enroll_face
from recognize import recognize_and_mark_attendance
from report import generate_report
from utils import prepare_image

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_image_for_enroll(image_path, user_id, name, image_array=None):
    try:
        if image_array is not None:
            image = prepare_image(image_array)
        else:
            image = prepare_image(image_path)
    except Exception as e:
        return False, f'Image processing error: {e}'
    boxes = face_recognition.face_locations(image)
    if not boxes:
        return False, 'No face detected.'
    encoding = face_recognition.face_encodings(image, boxes)[0]
    faces = load_faces_db()
    faces.append({'user_id': user_id, 'name': name, 'embedding': encoding})
    save_faces_db(faces)
    return True, f'Enrolled {name} ({user_id}) successfully.'

@app.route('/')
def index():
    from db import load_faces_db
    students = load_faces_db()
    student_count = len(students)
    return render_template('dashboard.html', students=students, student_count=student_count)

@app.route('/enroll', methods=['GET', 'POST'])
def enroll():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        name = request.form.get('name')
        file = request.files.get('image')
        webcam_image = request.form.get('webcam_image')
        if file and file.filename:
            # Save a permanent copy in uploads/enrolled/
            import time
            enrolled_dir = os.path.join(UPLOAD_FOLDER, 'enrolled')
            os.makedirs(enrolled_dir, exist_ok=True)
            timestamp = int(time.time())
            filename = f"{user_id}_{timestamp}_{file.filename}"
            enrolled_path = os.path.join(enrolled_dir, filename)
            file.save(enrolled_path)
            # Also process for face encoding
            success, msg = process_image_for_enroll(enrolled_path, user_id, name)
            flash(msg)
            return redirect(url_for('enroll'))
        elif webcam_image:
            # webcam_image is a data URL
            header, encoded = webcam_image.split(',', 1)
            data = base64.b64decode(encoded)
            npimg = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            if img is None:
                flash('Failed to decode webcam image. Please try again.')
                return redirect(url_for('enroll'))
            # Convert BGR to RGB (OpenCV uses BGR, face_recognition expects RGB)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            if img_rgb.dtype != np.uint8:
                img_rgb = img_rgb.astype(np.uint8)
            # Save webcam image as file for record
            enrolled_dir = os.path.join(UPLOAD_FOLDER, 'enrolled')
            os.makedirs(enrolled_dir, exist_ok=True)
            import time
            filename = f"{user_id}_{int(time.time())}_webcam.jpg"
            enrolled_path = os.path.join(enrolled_dir, filename)
            cv2.imwrite(enrolled_path, cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
            # Process the image array directly
            success, msg = process_image_for_enroll(enrolled_path, user_id, name)
            flash(msg)
            return redirect(url_for('enroll'))
        else:
            flash('Please upload an image or capture from webcam.')
            return redirect(url_for('enroll'))
    return render_template('enroll.html')

@app.route('/recognize', methods=['GET', 'POST'])
def recognize():
    result = None
    if request.method == 'POST':
        webcam_image = request.form.get('webcam_image')
        img_rgb = None
        if webcam_image:
            import base64
            import numpy as np
            import cv2
            header, encoded = webcam_image.split(',', 1)
            data = base64.b64decode(encoded)
            npimg = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            if img is None:
                flash('Failed to decode webcam image. Please try again.')
                return redirect(url_for('recognize'))
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            if img_rgb.dtype != np.uint8:
                img_rgb = img_rgb.astype(np.uint8)
        if img_rgb is not None:
            # Run recognition on the image
            faces = load_faces_db()
            if not faces:
                flash('No enrolled faces found.')
                return redirect(url_for('recognize'))
            known_embeddings = np.array([f['embedding'] for f in faces])
            user_ids = [f['user_id'] for f in faces]
            names = [f['name'] for f in faces]
            import face_recognition
            from utils import face_distance, is_match
            boxes = face_recognition.face_locations(img_rgb)
            encodings = face_recognition.face_encodings(img_rgb, boxes)
            found = False
            for encoding in encodings:
                distances = face_distance(known_embeddings, encoding, 'euclidean')
                idx, matched = is_match(distances, 0.6)
                if matched:
                    user_id = user_ids[idx]
                    name = names[idx]
                    from db import log_attendance
                    marked = log_attendance(user_id, name)
                    status = 'Present' if marked else 'Already marked today'
                    result = {'name': name, 'user_id': user_id, 'status': status}
                    found = True
                    break
            if not found:
                result = {'name': 'Unknown', 'user_id': '-', 'status': 'Not recognized'}
            return render_template('recognize.html', result=result)
        else:
            flash('Please capture an image from webcam.')
            return redirect(url_for('recognize'))
    return render_template('recognize.html', result=result)

@app.route('/report', methods=['GET', 'POST'])
def report():
    analytics_labels = []
    analytics_data = []
    enrollment_labels = []
    enrollment_data = []
    period = 'weekly'  # Default to last 7 days
    if request.method == 'POST':
        period = request.form.get('period', 'weekly')
    
    # Compute attendance analytics: number of students present per date
    from db import get_attendance_df, load_faces_db
    import pandas as pd
    df = get_attendance_df()
    df = pd.DataFrame(df)
    df['date'] = df['date'].astype(str)
    today = pd.to_datetime('today').normalize()
    if period == 'daily':
        date_list = [today.strftime('%Y-%m-%d')]
        df_period = df[df['date'] == date_list[0]]
    elif period == 'weekly':
        week_ago = today - pd.Timedelta(days=7)
        date_range = pd.date_range(week_ago, today)
        date_list = date_range.strftime('%Y-%m-%d').tolist()
        df_period = df[df['date'].isin(date_list)]
    elif period == 'monthly':
        month = today.strftime('%Y-%m')
        df_period = df[df['date'].str.startswith(month)]
        df_period = pd.DataFrame(df_period)
        date_list = sorted(list(df_period['date'].unique()))
    else:
        date_list = []
        df_period = df.iloc[0:0]
    analytics_labels = date_list
    analytics_data = []
    for d in date_list:
        status_series = pd.Series(df_period['status']) if 'status' in df_period else pd.Series([])
        present_mask = (df_period['date'] == d) & (status_series.astype(str).str.lower() == 'present')
        present_count = df_period.loc[present_mask, 'user_id'].nunique()
        analytics_data.append(int(present_count))

    # Compute enrollment analytics: number of students enrolled per date
    import os
    import re
    enrolled_dir = os.path.join('uploads', 'enrolled')
    enroll_dates = {}
    if os.path.exists(enrolled_dir):
        for fname in os.listdir(enrolled_dir):
            # Expect filename format: user_id_timestamp_filename.jpg
            match = re.match(r'.*_(\d+)_.*', fname)
            if match:
                timestamp = int(match.group(1))
                date = pd.to_datetime(timestamp, unit='s').strftime('%Y-%m-%d')
                enroll_dates.setdefault(date, 0)
                enroll_dates[date] += 1
    # Build enrollment data for the same date_list
    enrollment_labels = date_list
    enrollment_data = [enroll_dates.get(d, 0) for d in date_list]

    from db import load_faces_db
    students = load_faces_db()

    if request.method == 'POST':
        # Generate CSV report for the selected period
        if df_period.empty:
            flash('No attendance data found for the selected period.')
            return redirect(url_for('report'))
        # Create a filtered CSV for the selected period
        csv_filename = f"attendance_{period}_{today.strftime('%Y-%m-%d')}.csv"
        csv_path = os.path.join('data', 'reports', csv_filename)
        os.makedirs('data/reports', exist_ok=True)
        # Save the filtered data as CSV
        df_period.to_csv(csv_path, index=False)
        if os.path.exists(csv_path):
            return send_from_directory('data/reports', csv_filename, as_attachment=True)
        else:
            flash('Failed to generate CSV report.')
            return redirect(url_for('report'))
    return render_template('report.html', analytics_labels=analytics_labels, analytics_data=analytics_data, enrollment_labels=enrollment_labels, enrollment_data=enrollment_data, students=students)

@app.route('/export_attendance')
def export_attendance():
    path = os.path.join('data', 'attendance.csv')
    if os.path.exists(path):
        return send_from_directory('data', 'attendance.csv', as_attachment=True)
    else:
        flash('Attendance file not found.')
        return redirect(url_for('index'))

@app.route('/download_complete_attendance')
def download_complete_attendance():
    """Download the complete attendance CSV file"""
    path = os.path.join('data', 'attendance.csv')
    if os.path.exists(path):
        return send_from_directory('data', 'attendance.csv', as_attachment=True)
    else:
        flash('Attendance file not found.')
        return redirect(url_for('report'))

@app.route('/delete_student', methods=['POST'])
def delete_student():
    user_id = request.form.get('user_id')
    if not user_id:
        flash('No user ID provided for deletion.')
        return redirect(url_for('report'))
    from db import load_faces_db, save_faces_db
    import os
    import pandas as pd
    faces = load_faces_db()
    new_faces = [f for f in faces if f['user_id'] != user_id]
    save_faces_db(new_faces)
    # Delete images from uploads/enrolled/
    enrolled_dir = os.path.join('uploads', 'enrolled')
    if os.path.exists(enrolled_dir):
        for fname in os.listdir(enrolled_dir):
            if fname.startswith(user_id + '_') or f'_{user_id}_' in fname:
                try:
                    os.remove(os.path.join(enrolled_dir, fname))
                except Exception:
                    pass
    # Delete attendance records from data/attendance.csv
    attendance_path = os.path.join('data', 'attendance.csv')
    if os.path.exists(attendance_path):
        df = pd.read_csv(attendance_path)
        df = df[df['user_id'] != user_id]
        df.to_csv(attendance_path, index=False)
    flash(f'Student with ID {user_id} and all their data deleted.')
    return redirect(url_for('report'))

if __name__ == '__main__':
    app.run(debug=True) 