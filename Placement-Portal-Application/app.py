from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "placement_portal.db"

# ==================================================
# ROLE DECORATORS
# ==================================================

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "student" not in session:
            return redirect(url_for("student_login"))
        return f(*args, **kwargs)
    return decorated_function


def company_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "company" not in session:
            return redirect(url_for("company_login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin" not in session:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():
    return "<h2>Placement Portal Running Successfully!</h2>"


# ==================================================
# ADMIN SECTION
# ==================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM Admin WHERE username = ?", (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and check_password_hash(admin[2], password):
            session.clear()
            session["admin"] = admin[0]
            return redirect(url_for("admin_dashboard"))

        return "Invalid credentials"

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Company")
    total_companies = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Student")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM JobPosition")
    total_jobs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Application")
    total_applications = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Placement")
    total_placements = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        companies=total_companies,
        students=total_students,
        jobs=total_jobs,
        applications=total_applications,
        placements=total_placements
    )


# ---------------- MANAGE STUDENTS ----------------

@app.route("/admin/manage_students")
@admin_required
def manage_students():

    search_query = request.args.get("search", "")

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if search_query:
        cursor.execute("""
            SELECT * FROM Student
            WHERE full_name LIKE ?
            OR email LIKE ?
        """, (f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT * FROM Student")

    students = cursor.fetchall()
    conn.close()

    return render_template("manage_students.html",
                           students=students,
                           search_query=search_query)


@app.route("/admin/blacklist/student/<int:student_id>")
@admin_required
def blacklist_student(student_id):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Student
        SET is_blacklisted = 1
        WHERE id = ?
    """, (student_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("manage_students"))


# ---------------- MANAGE COMPANIES ----------------

@app.route("/admin/manage_companies")
@admin_required
def manage_companies():

    search_query = request.args.get("search", "")

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if search_query:
        cursor.execute("""
            SELECT * FROM Company
            WHERE name LIKE ?
            OR email LIKE ?
            OR industry LIKE ?
        """, (f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT * FROM Company")

    companies = cursor.fetchall()
    conn.close()

    return render_template("manage_companies.html",
                           companies=companies,
                           search_query=search_query)


@app.route("/admin/company/<int:company_id>/<string:action>")
@admin_required
def update_company_status(company_id, action):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if action == "approve":
        cursor.execute("UPDATE Company SET approval_status='Approved' WHERE id=?", (company_id,))
    elif action == "reject":
        cursor.execute("UPDATE Company SET approval_status='Rejected' WHERE id=?", (company_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("manage_companies"))


@app.route("/admin/blacklist/company/<int:company_id>")
@admin_required
def blacklist_company(company_id):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("UPDATE Company SET is_blacklisted=1 WHERE id=?", (company_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("manage_companies"))


# ---------------- MANAGE JOBS ----------------

@app.route("/admin/manage_jobs")
@admin_required
def manage_jobs():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT JobPosition.*, Company.name
        FROM JobPosition
        JOIN Company ON JobPosition.company_id = Company.id
    """)

    jobs = cursor.fetchall()
    conn.close()

    return render_template("manage_jobs.html", jobs=jobs)


@app.route("/admin/job/<int:job_id>/<string:action>")
@admin_required
def update_job_status(job_id, action):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if action == "approve":
        cursor.execute("UPDATE JobPosition SET approval_status='Approved' WHERE id=?", (job_id,))
    elif action == "reject":
        cursor.execute("UPDATE JobPosition SET approval_status='Rejected' WHERE id=?", (job_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("manage_jobs"))


# ---------------- MANAGE APPLICATIONS ----------------

@app.route("/admin/manage_applications")
@admin_required
def manage_applications():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Application.id,
               Application.status,
               Student.full_name AS student_name,
               JobPosition.title AS job_title
        FROM Application
        JOIN Student ON Application.student_id = Student.id
        JOIN JobPosition ON Application.job_id = JobPosition.id
    """)

    applications = cursor.fetchall()
    conn.close()

    return render_template("manage_applications.html", applications=applications)


# ==================================================
# COMPANY SECTION
# ==================================================

@app.route("/company/register", methods=["GET", "POST"])
def company_register():

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO Company (name, email, password_hash, approval_status, is_blacklisted)
                VALUES (?, ?, ?, 'Pending', 0)
            """, (name, email, hashed_password))

            conn.commit()
            conn.close()
            return "Registration Successful! Wait for Admin Approval."

        except sqlite3.IntegrityError:
            conn.close()
            return "Email already exists!"

    return render_template("company_register.html")


@app.route("/company/login", methods=["GET", "POST"])
def company_login():

    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, password_hash, approval_status, is_blacklisted
            FROM Company
            WHERE email = ?
        """, (email,))

        company = cursor.fetchone()
        conn.close()

        if not company:
            return "Invalid email or password"

        company_id, stored_password, approval_status, is_blacklisted = company

        if is_blacklisted == 1:
            return "Your company has been blacklisted."

        if approval_status != "Approved":
            return "Your account is pending admin approval."

        if not check_password_hash(stored_password, password):
            return "Invalid email or password"

        session.clear()
        session["company"] = company_id

        return redirect(url_for("company_dashboard"))

    return render_template("company_login.html")


@app.route("/company/dashboard")
@company_required
def company_dashboard():
    return "<h2>Welcome Company! Login Successful 🎉</h2>"


# ==================================================
# STUDENT SECTION
# ==================================================

@app.route("/student/register", methods=["GET", "POST"])
def student_register():

    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO Student (full_name, email, password_hash, is_blacklisted)
                VALUES (?, ?, ?, 0)
            """, (full_name, email, hashed_password))

            conn.commit()
            conn.close()
            return "Student Registration Successful!"

        except sqlite3.IntegrityError:
            conn.close()
            return "Email already exists!"

    return render_template("student_register.html")


@app.route("/student/login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, password_hash, is_blacklisted
            FROM Student
            WHERE email = ?
        """, (email,))

        student = cursor.fetchone()
        conn.close()

        if not student:
            return "Invalid Credentials"

        student_id, stored_password, is_blacklisted = student

        if is_blacklisted == 1:
            return "Your account has been blacklisted."

        if not check_password_hash(stored_password, password):
            return "Invalid Credentials"

        session.clear()
        session["student"] = student_id

        return redirect(url_for("student_dashboard"))

    return render_template("student_login.html")


@app.route("/student/dashboard")
@student_required
def student_dashboard():
    return render_template("student_dashboard.html")


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ==================================================
# RUN APP
# ==================================================

if __name__ == "__main__":
    app.run(debug=True)