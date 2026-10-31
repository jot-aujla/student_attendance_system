from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
from datetime import date

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
DB_PATH = os.path.join(os.path.dirname(__file__), "attendance.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('hod', 'faculty')),
            full_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            section TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
            marked_by INTEGER NOT NULL,
            UNIQUE(student_id, attendance_date),
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY(marked_by) REFERENCES users(id)
        );
        """)
        # Demo accounts are created only if they do not already exist.
        defaults = [
            ("hod", generate_password_hash("hod123"), "hod", "Head of Department"),
            ("faculty", generate_password_hash("faculty123"), "faculty", "Demo Faculty")
        ]
        for user in defaults:
            db.execute("INSERT OR IGNORE INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)", user)
        count = db.execute("SELECT COUNT(*) AS n FROM students").fetchone()["n"]
        if count == 0:
            demo_students = [
                ("CSE001", "Aarav Sharma", "CSE-A"),
                ("CSE002", "Simran Kaur", "CSE-A"),
                ("CSE003", "Arjun Singh", "CSE-A"),
                ("CSE004", "Mehak Verma", "CSE-B"),
                ("CSE005", "Kabir Gill", "CSE-B"),
                ("CSE006", "Navya Gupta", "CSE-B"),
            ]
            db.executemany("INSERT INTO students (roll_no, full_name, section) VALUES (?, ?, ?)", demo_students)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") != role:
                flash("You do not have permission to access that page.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], username=user["username"], role=user["role"], full_name=user["full_name"])
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today().isoformat()
    with get_db() as db:
        total_students = db.execute("SELECT COUNT(*) n FROM students").fetchone()["n"]
        sections = db.execute("SELECT DISTINCT section FROM students ORDER BY section").fetchall()
        today_stats = db.execute("""
            SELECT status, COUNT(*) n FROM attendance
            WHERE attendance_date = ? GROUP BY status
        """, (today,)).fetchall()
        recent = db.execute("""
            SELECT a.attendance_date, a.status, s.roll_no, s.full_name, s.section
            FROM attendance a JOIN students s ON s.id=a.student_id
            ORDER BY a.attendance_date DESC, a.id DESC LIMIT 6
        """).fetchall()
    stats = {row["status"]: row["n"] for row in today_stats}
    return render_template("dashboard.html", total_students=total_students,
                           sections=sections, present=stats.get("Present", 0),
                           absent=stats.get("Absent", 0), today=today, recent=recent)

@app.route("/students", methods=["GET", "POST"])
@role_required("hod")
def students():
    with get_db() as db:
        if request.method == "POST":
            action = request.form.get("action")
            if action == "add":
                roll_no = request.form.get("roll_no", "").strip().upper()
                full_name = request.form.get("full_name", "").strip()
                section = request.form.get("section", "").strip().upper()
                if not roll_no or not full_name or not section:
                    flash("Please fill in every student field.", "error")
                else:
                    try:
                        db.execute("INSERT INTO students (roll_no, full_name, section) VALUES (?, ?, ?)",
                                   (roll_no, full_name, section))
                        flash("Student added successfully.", "success")
                    except sqlite3.IntegrityError:
                        flash("That roll number already exists.", "error")
            elif action == "delete":
                student_id = request.form.get("student_id", type=int)
                db.execute("DELETE FROM students WHERE id = ?", (student_id,))
                flash("Student removed. Their attendance records were also deleted.", "success")
            return redirect(url_for("students"))
        student_rows = db.execute("SELECT * FROM students ORDER BY section, roll_no").fetchall()
    return render_template("students.html", students=student_rows)

@app.route("/attendance", methods=["GET", "POST"])
@role_required("faculty")
def attendance():
    with get_db() as db:
        sections = db.execute("SELECT DISTINCT section FROM students ORDER BY section").fetchall()
        section_names = [row["section"] for row in sections]
        selected_section = request.values.get("section", "")
        selected_date = request.values.get("attendance_date", date.today().isoformat())
        if selected_section not in section_names:
            selected_section = section_names[0] if section_names else ""
        if request.method == "POST":
            if not selected_section:
                flash("There are no student sections yet. Ask the HOD to add students.", "error")
                return redirect(url_for("attendance"))
            students_in_section = db.execute("SELECT id FROM students WHERE section = ?", (selected_section,)).fetchall()
            try:
                for student in students_in_section:
                    status = "Present" if request.form.get(f"status_{student['id']}") == "Present" else "Absent"
                    db.execute("""
                        INSERT INTO attendance (student_id, attendance_date, status, marked_by)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(student_id, attendance_date)
                        DO UPDATE SET status=excluded.status, marked_by=excluded.marked_by
                    """, (student["id"], selected_date, status, session["user_id"]))
                flash(f"Attendance saved for {selected_section} on {selected_date}.", "success")
            except sqlite3.Error:
                flash("Could not save attendance. Please try again.", "error")
            return redirect(url_for("attendance", section=selected_section, attendance_date=selected_date))
        roster = db.execute("""
            SELECT s.*, a.status FROM students s
            LEFT JOIN attendance a ON a.student_id=s.id AND a.attendance_date=?
            WHERE s.section=? ORDER BY s.roll_no
        """, (selected_date, selected_section)).fetchall() if selected_section else []
    return render_template("attendance.html", sections=section_names, selected_section=selected_section,
                           selected_date=selected_date, roster=roster)

@app.route("/report")
@login_required
def report():
    section = request.args.get("section", "").strip()
    attendance_date = request.args.get("attendance_date", date.today().isoformat())
    with get_db() as db:
        sections = [r["section"] for r in db.execute("SELECT DISTINCT section FROM students ORDER BY section").fetchall()]
        query = """
            SELECT s.roll_no, s.full_name, s.section, a.status, a.attendance_date
            FROM students s LEFT JOIN attendance a
            ON a.student_id=s.id AND a.attendance_date=?
        """
        params = [attendance_date]
        if section:
            query += " WHERE s.section=?"
            params.append(section)
        query += " ORDER BY s.section, s.roll_no"
        rows = db.execute(query, params).fetchall()
    return render_template("report.html", rows=rows, sections=sections, selected_section=section,
                           selected_date=attendance_date)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
