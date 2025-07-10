import pandas as pd
from db import get_attendance_df
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import xlsxwriter
import os

def generate_report(period='daily', fmt='pdf'):
    df = get_attendance_df()
    if df.empty:
        print('No attendance records found.')
        return
    today = datetime.now().date()
    if period == 'daily':
        df = df[df['date'] == today.strftime('%Y-%m-%d')]
        report_name = f'report_{today}.{{}}'
    elif period == 'weekly':
        week_ago = today - timedelta(days=7)
        df = df[(df['date'] >= week_ago.strftime('%Y-%m-%d')) & (df['date'] <= today.strftime('%Y-%m-%d'))]
        report_name = f'report_week_{today}.{{}}'
    elif period == 'monthly':
        month = today.strftime('%Y-%m')
        df = df[df['date'].str.startswith(month)]
        report_name = f'report_{month}.{{}}'
    else:
        print('Invalid period.')
        return
    # Ensure df is a pandas DataFrame
    df = pd.DataFrame(df)
    date_list = sorted(list(df['date'].unique()))
    students = pd.DataFrame(df[['user_id', 'name']].drop_duplicates())
    summary_rows = []
    for _, student in students.iterrows():
        user_id = student['user_id']
        name = student['name']
        group = df[(df['user_id'] == user_id) & (df['name'] == name)]
        group = pd.DataFrame(group)
        status_list = []
        for date in date_list:
            day_row = group[group['date'] == date]
            day_row = pd.DataFrame(day_row)
            if not day_row.empty:
                day_status = day_row['status'].iloc[0]
            else:
                day_status = 'absent'
            status_list.append(day_status.lower())
        summary_rows.append({'User_id': user_id, 'name': name, 'Dates': ', '.join(status_list)})
    summary_df = pd.DataFrame(summary_rows)
    out_dir = 'data/reports'
    os.makedirs(out_dir, exist_ok=True)
    if fmt == 'pdf':
        path = os.path.join(out_dir, report_name.format('pdf'))
        c = canvas.Canvas(path, pagesize=letter)
        c.drawString(30, 750, f'Attendance Report ({period.capitalize()})')
        y = 720
        col_names = list(summary_df.columns)
        col_str = ' | '.join(col_names)
        c.drawString(30, y, col_str)
        y -= 20
        for i, row in summary_df.iterrows():
            row_str = ' | '.join(str(row[col]) for col in col_names)
            c.drawString(30, y, row_str)
            y -= 20
            if y < 50:
                c.showPage()
                y = 750
                c.drawString(30, y, col_str)
                y -= 20
        c.save()
        print(f'PDF report saved to {path}')
    elif fmt == 'xlsx' or fmt == 'csv':
        ext = 'xlsx' if fmt == 'xlsx' else 'csv'
        path = os.path.join(out_dir, report_name.format(ext))
        if fmt == 'xlsx':
            writer = pd.ExcelWriter(path, engine='xlsxwriter')
            summary_df.to_excel(writer, index=False)
            writer.close()
        else:
            summary_df.to_csv(path, index=False)
        print(f'{ext.upper()} report saved to {path}')
    else:
        print('Invalid format.') 