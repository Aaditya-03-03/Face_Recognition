from enroll import enroll_face
from recognize import recognize_and_mark_attendance
from report import generate_report

def main():
    print('''\nFacial Recognition Attendance System\n''')
    while True:
        print('\nOptions:')
        print('1. Enroll new face')
        print('2. Start attendance (recognition)')
        print('3. Generate report')
        print('4. Exit')
        choice = input('Select option: ')
        if choice == '1':
            enroll_face()
        elif choice == '2':
            recognize_and_mark_attendance()
        elif choice == '3':
            period = input('Report period (daily/weekly/monthly): ').strip().lower()
            fmt = input('Format (pdf/xlsx): ').strip().lower()
            generate_report(period, fmt)
        elif choice == '4':
            print('Goodbye!')
            break
        else:
            print('Invalid option.')

if __name__ == '__main__':
    main() 