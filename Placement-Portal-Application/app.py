from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "placement_portal.db"


# ==================================================
# ROLE DECORATORS (DEFINED ONLY ONCE)
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
        cursor.execute("SELECT password_hash FROM Admin WHERE username = ?", (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and check_password_hash(admin[0], password):
            session["admin"] = username
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin_login.html", error="Invalid Credentials")

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM Company WHERE approval_status = 'Pending'")
    pending_companies = cursor.fetchall()

    connection.close()

    return render_template("admin_dashboard.html", companies=pending_companies)


@app.route("/admin/approve_company/<int:company_id>")
@admin_required
def approve_company(company_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE Company
        SET approval_status = 'Approved'
        WHERE id = ?
    """, (company_id,))

    connection.commit()
    connection.close()

    return redirect(url_for("admin_dashboard"))


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
                INSERT INTO Company (name, email, password_hash, approval_status)
                VALUES (?, ?, ?, 'Pending')
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
        email = request.form["email"]
        password = request.form["password"]

        connection = sqlite3.connect(DB_NAME)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Company WHERE email = ?", (email,))
        company = cursor.fetchone()
        connection.close()

        if company and check_password_hash(company[3], password):

            if company[4] != "Approved":
                return "Your account is pending admin approval."

            session["company"] = company[0]
            return redirect(url_for("company_dashboard"))

        return "Invalid email or password"

    return render_template("company_login.html")


@app.route("/company/dashboard")
@company_required
def company_dashboard():
    return "<h2>Welcome Company! Login Successful 🎉</h2>"


@app.route("/company/post_job", methods=["GET", "POST"])
@company_required
def post_job():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        location = request.form["location"]
        ctc = request.form["ctc"]
        deadline = request.form["deadline"]

        connection = sqlite3.connect(DB_NAME)
        cursor = connection.cursor()

        cursor.execute("""
        INSERT INTO JobPosition (company_id, title, description, location, ctc, deadline)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (session["company"], title, description, location, ctc, deadline))

        connection.commit()
        connection.close()

        return "Job Posted Successfully!"

    return render_template("post_job.html")


@app.route("/company/update_status/<int:application_id>/<string:new_status>")
@company_required
def update_status(application_id, new_status):

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Update application status
    cursor.execute("""
    UPDATE Application
    SET status = ?, last_updated = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (new_status, application_id))

    # ---------------- AUTO CREATE PLACEMENT ----------------
    if new_status == "Selected":

        # Check if placement already exists
        cursor.execute("""
        SELECT id FROM Placement
        WHERE application_id = ?
        """, (application_id,))

        placement_exists = cursor.fetchone()

        if not placement_exists:
            cursor.execute("""
            INSERT INTO Placement (application_id, offer_package, joining_date)
            VALUES (?, ?, ?)
            """, (application_id, "6 LPA", None))   # Default package (can customize later)

    connection.commit()
    connection.close()

    return redirect(request.referrer)


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
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, password_hash, is_blacklisted
            FROM Student WHERE email = ?
        """, (email,))
        student = cursor.fetchone()
        conn.close()

        if not student:
            return "Invalid Credentials"

        student_id, stored_password, is_blacklisted = student

        if is_blacklisted == 1:
            return "You are blacklisted by Admin."

        if check_password_hash(stored_password, password):
            session["student"] = student_id
            return redirect(url_for("student_dashboard"))

        return "Invalid Credentials"

    return render_template("student_login.html")


@app.route("/student/dashboard")
@student_required
def student_dashboard():
    return render_template("student_dashboard.html")


@app.route("/student/jobs")
@student_required
def view_jobs():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    SELECT JobPosition.id, Company.name, title, location, ctc, deadline
    FROM JobPosition
    JOIN Company ON JobPosition.company_id = Company.id
    """)

    jobs = cursor.fetchall()
    connection.close()

    return render_template("student_jobs.html", jobs=jobs)


@app.route("/student/apply/<int:job_id>")
@student_required
def apply_job(job_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    try:
        cursor.execute("""
        INSERT INTO Application (student_id, job_id)
        VALUES (?, ?)
        """, (session["student"], job_id))

        connection.commit()
        message = "Application Submitted Successfully!"

    except sqlite3.IntegrityError:
        message = "You have already applied to this job."

    connection.close()
    return message


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