# Attendly — Student Attendance Management System

A Python Flask web project with two roles: **HOD** and **Faculty**. Uses SQLite, so no separate database server is needed.

## Features
- Role-based sign-in for HOD and Faculty.
- HOD can add students, assign a section, and remove students.
- Faculty selects a section and date before marking attendance.
- Present/Absent controls for each student; absent rows highlight red.
- Attendance is saved to SQLite and can be updated for the same date.
- Daily attendance report with section/date filters and print support.
- Dashboard with student, section, present and absent counts.

## Requirements
- Python 3.10 or newer recommended
- pip

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted `student_attendance_system` folder in VS Code.
3. Open the terminal in that folder.
4. (Recommended) Create a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and run the app with `.\.venv\Scripts\python.exe app.py`.
5. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
6. Start the website:
   ```powershell
   python app.py
   ```
7. Open **http://127.0.0.1:5000** in your browser.

The database `attendance.db` is created automatically the first time the app starts. Demo student records are included.

## Demo login
| Role | Username | Password |
|---|---|---|
| HOD | `hod` | `hod123` |
| Faculty | `faculty` | `faculty123` |

## Project structure
```text
student_attendance_system/
├── app.py
├── attendance.db       # created automatically when app.py runs
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── students.html
│   ├── attendance.html
│   └── report.html
└── static/
    └── style.css
```

## Important notes
- Demo credentials are for a classroom project only. Change them and set a strong `SECRET_KEY` before any real deployment.
- This is a learning/demo app, not a hardened production system. For a real deployment, add CSRF protection, account management, audit logs, secure production configuration, and HTTPS.
- Removing a student also removes their attendance records, as shown in the confirmation prompt.
