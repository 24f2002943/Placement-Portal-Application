from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.utils import secure_filename

def get_db_connection():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS



app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads/resumes"
ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS



DB_NAME = "placement_portal.db"




# ==================================================
# ROLE DECORATORS
# ==================================================

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "student_id" not in session:
            return redirect(url_for("student_login"))
        return f(*args, **kwargs)
    return decorated_function


def company_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "company_id" not in session:
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




from flask import send_from_directory

@app.route("/resume/<filename>")
@company_required
def download_resume(filename):

    upload_folder = "uploads"
    return send_from_directory(upload_folder, filename)


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

        print("Entered Username:", username)
        print("Entered Password:", password)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM Admin WHERE username = ?", (username,))
        admin = cursor.fetchone()
        conn.close()

        print("Admin from DB:", admin)

        if admin:
            print("Stored Hash:", admin[2])
            print("Password Match:",
                  check_password_hash(admin[2], password))

        if admin and check_password_hash(admin[2], password):
            session.clear()
            session["admin"] = admin[0]

            print("Session after login:", dict(session))

            return redirect(url_for("admin_dashboard"))

        print("Login Failed")
        return "Invalid credentials"

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Company")
    total_companies = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Student")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM PlacementDrive")
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


#----------- MANAGE STUDENTS ----------------
@app.route("/admin/manage_students")
@admin_required
def manage_students():

    search_query = request.args.get("search", "").strip()

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if search_query:
        cursor.execute("""
            SELECT *
            FROM Student
            WHERE full_name LIKE ?
               OR email LIKE ?
               OR phone LIKE ?
        """, (
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%"
        ))
    else:
        cursor.execute("SELECT * FROM Student")

    students = cursor.fetchall()
    conn.close()

    return render_template(
        "manage_students.html",
        students=students,
        search_query=search_query
    )

@app.route("/admin/blacklist/student/<int:student_id>")
@admin_required
def blacklist_student(student_id):

    conn = get_db_connection()
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

    search_query = request.args.get("search", "").strip()

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if search_query:
        cursor.execute("""
            SELECT * FROM Company
            WHERE name LIKE ?
            OR email LIKE ?
        
        """, (f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT * FROM Company")

    companies = cursor.fetchall()
    conn.close()

    return render_template("manage_companies.html",
                           companies=companies,
                           search_query=search_query)

@app.route("/admin/companies")
def admin_view_companies():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email, location, approval_status, is_blacklisted
        FROM Company
        ORDER BY approval_status
    """)

    companies = cursor.fetchall()
    conn.close()

    return render_template("admin_companies.html", companies=companies)


@app.route("/admin/company/approve/<int:company_id>")
def approve_company(company_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Company
        SET approval_status = 'Approved'
        WHERE id = ?
    """, (company_id,))

    conn.commit()
    conn.close()

    flash("Company Approved Successfully!", "success")
    return redirect(url_for("admin_view_companies"))

@app.route("/admin/company/reject/<int:company_id>")
def reject_company(company_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Company
        SET approval_status = 'Rejected'
        WHERE id = ?
    """, (company_id,))

    conn.commit()
    conn.close()

    flash("Company Rejected!", "danger")
    return redirect(url_for("admin_view_companies"))


@app.route("/admin/blacklist/company/<int:company_id>")
@admin_required
def blacklist_company(company_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE Company SET is_blacklisted=1 WHERE id=?", (company_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("manage_companies"))


#------------ MANAGE JOBS ----------------
@app.route("/admin/manage_jobs")
@admin_required
def manage_jobs():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT PlacementDrive.*, Company.name
        FROM PlacementDrive
        JOIN Company ON PlacementDrive.company_id = Company.id
    """)

    jobs = cursor.fetchall()
    conn.close()

    return render_template("manage_jobs.html", jobs=jobs)


@app.route("/admin/job/<int:drive_id>/<string:action>")
@admin_required
def update_job_status(drive_id, action):

    conn = get_db_connection()
    cursor = conn.cursor()

    if action == "approve":
        cursor.execute("UPDATE PlacementDrive SET approval_status='Approved' WHERE id=?", (drive_id,))
    elif action == "reject":
        cursor.execute("UPDATE PlacementDrive SET approval_status='Rejected' WHERE id=?", (drive_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("manage_jobs"))


# ---------------- MANAGE APPLICATIONS ----------------

@app.route("/admin/manage_applications")
@admin_required
def manage_applications():

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Application.id,
               Application.status,
               Student.full_name AS student_name,
               PlacementDrive.title AS drive_title
        FROM Application
        JOIN Student ON Application.student_id = Student.id
        JOIN PlacementDrive ON Application.drive_id = PlacementDrive.id
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

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        location = request.form.get("location", "").strip()
        industry = request.form.get("industry", "").strip()


        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("company_register"))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT id FROM Company WHERE email = ?", (email,))
        existing_company = cursor.fetchone()

        if existing_company:
            conn.close()
            flash("Email already registered.", "warning")
            return redirect(url_for("company_register"))

        hashed_password = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO Company (name, email, password_hash, location, industry, approval_status, is_blacklisted)
            VALUES (?, ?, ?, ?,? ,'Pending', 0)
        """, (name, email, hashed_password, location, industry))

        conn.commit()
        conn.close()

        flash("Registration successful! Wait for admin approval.", "success")
        return redirect(url_for("company_login"))

    return render_template("company_register.html")


@app.route("/company/login", methods=["GET", "POST"])
def company_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return redirect(url_for("company_login"))

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM Company
            WHERE email = ?
        """, (email,))

        company = cursor.fetchone()




        if not company:
            conn.close()
            flash("Invalid email or password.", "danger")
            return redirect(url_for("company_login"))

        # Check blacklist
        if company["is_blacklisted"] == 1:
            conn.close()
            flash("Your company account has been blacklisted. Contact admin.", "danger")
            return redirect(url_for("company_login"))

        # Check approval status
        if company["approval_status"] == "Pending":
            conn.close()
            flash("Your account is pending admin approval.", "warning")
            return redirect(url_for("company_login"))

        if company["approval_status"] == "Rejected":
            conn.close()
            flash("Your registration has been rejected by admin.", "danger")
            return redirect(url_for("company_login"))

        # Verify password
        if not check_password_hash(company["password_hash"], password):
            conn.close()
            flash("Invalid email or password.", "danger")
            return redirect(url_for("company_login"))

        # Update last login time
        cursor.execute("""
            UPDATE Company
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (company["id"],))

        conn.commit()
        conn.close()

        # Set session
        session.clear()
        session["company_id"] = company["id"]
        session["company_name"] = company["name"]

        print("Company session after login:", dict(session)) 

        flash("Login successful!", "success")
         # DEBUG LINE
        return redirect(url_for("company_dashboard"))
    
    return render_template("company_login.html")


@app.route("/company/dashboard")
@company_required
def company_dashboard():

    company_id = session["company_id"]

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM PlacementDrive WHERE company_id=?", (company_id,))
    total_jobs = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM PlacementDrive
        WHERE company_id=? AND drive_status='Active'
    """, (company_id,))
    active_jobs = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM PlacementDrive
        WHERE company_id=? AND drive_status='Closed'
    """, (company_id,))
    closed_jobs = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM Application
        JOIN PlacementDrive ON Application.drive_id = PlacementDrive.id
        WHERE PlacementDrive.company_id=?
    """, (company_id,))
    total_applications = cursor.fetchone()[0]

    cursor.execute("""
        SELECT * FROM PlacementDrive
        WHERE company_id=?
    """, (company_id,))
    jobs = cursor.fetchall()

    conn.close()

    return render_template(
        "company_dashboard.html",
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        closed_jobs=closed_jobs,
        total_applications=total_applications,
        jobs=jobs
    )

@app.route("/company/post_drive", methods=["GET", "POST"])
@company_required
def post_drive():

    company_id = session["company_id"]

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        location = request.form["location"]
        required_skills = request.form["required_skills"]
        experience_required = request.form["experience_required"]
        min_salary = request.form["min_salary"]
        max_salary = request.form["max_salary"]
        deadline = request.form["deadline"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO PlacementDrive
            (company_id, title, description, location,
             required_skills, experience_required,
             min_salary, max_salary, deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            title,
            description,
            location,
            required_skills,
            experience_required,
            min_salary,
            max_salary,
            deadline
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("company_dashboard"))

    return render_template("post_job.html")




@app.route("/company/drive/<int:drive_id>/applications")
@company_required
def view_job_applications(drive_id):

    company_id = session["company_id"]

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM PlacementDrive
        WHERE id=? AND company_id=?
    """, (drive_id, company_id))

    job = cursor.fetchone()

    if not job:
        conn.close()
        return "Unauthorized access"

    cursor.execute("""
        SELECT Application.id,
               Application.status,
               Application.applied_at,
               Student.id AS student_id,
               Student.full_name,
               Student.email,
               Student.phone,
               Application.resume_snapshot_path
        FROM Application
        JOIN Student ON Application.student_id = Student.id
        WHERE Application.drive_id=?
    """, (drive_id,))

    applications = cursor.fetchall()

    conn.close()

    return render_template(
        "view_applications.html",
        job=job,
        applications=applications
    )


@app.route("/company/drive/<int:drive_id>/toggle")
@company_required
def toggle_drive_status(drive_id):

    company_id = session["company_id"]

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Ensure drive belongs to this company
    cursor.execute("""
        SELECT *
        FROM PlacementDrive
        WHERE id=? AND company_id=?
    """, (drive_id, company_id))

    drive = cursor.fetchone()

    if not drive:
        conn.close()
        return "Unauthorized action"

    # Correct column name
    new_status = "Closed" if drive["drive_status"] == "Active" else "Active"

    cursor.execute("""
        UPDATE PlacementDrive
        SET drive_status=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (new_status, drive_id))

    conn.commit()
    conn.close()

    return redirect(url_for("company_dashboard"))


@app.route("/company/application/<int:application_id>/<string:new_status>")
@company_required
def update_application_status(application_id, new_status):

    company_id = session["company_id"]
    allowed_status = ["Shortlisted", "Selected", "Rejected"]

    if new_status not in allowed_status:
        return "Invalid status"

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Application.*, PlacementDrive.company_id
        FROM Application
        JOIN PlacementDrive ON Application.drive_id = PlacementDrive.id
        WHERE Application.id=?
    """, (application_id,))

    application = cursor.fetchone()

    if not application or application["company_id"] != company_id:
        conn.close()
        return "Unauthorized action"

    cursor.execute("""
        UPDATE Application
        SET status=?
        WHERE id=?
    """, (new_status, application_id))

    if new_status == "Selected":

        cursor.execute("""
            SELECT * FROM Placement
            WHERE application_id=?
        """, (application_id,))

        existing = cursor.fetchone()

        if not existing:
            cursor.execute("""
                INSERT INTO Placement (application_id)
                VALUES (?)
            """, (application_id,))

    conn.commit()
    conn.close()

    return redirect(url_for(
        "view_job_applications",
        drive_id=application["drive_id"]
    ))

@app.route("/company/update_status/<int:application_id>", methods=["POST"])
def company_update_status(application_id):

    if "company_id" not in session:
        return redirect(url_for("company_login"))

    company_id = session["company_id"]

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    new_status = request.form.get("status")

    if new_status not in ["Applied", "Shortlisted", "Interview", "Rejected", "Placed"]:
        conn.close()
        return "Invalid status."

    # -------- FETCH APPLICATION + OWNERSHIP CHECK --------
    cursor.execute("""
        SELECT Application.student_id,
               Application.status,
               PlacementDrive.company_id
        FROM Application
        JOIN PlacementDrive
            ON Application.drive_id = PlacementDrive.id
        WHERE Application.id = ?
    """, (application_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return "Application not found."

    student_id = row["student_id"]
    current_status = row["status"]
    drive_company_id = row["company_id"]

    # -------- SECURITY: COMPANY CAN ONLY MODIFY ITS OWN DRIVE --------
    if drive_company_id != company_id:
        conn.close()
        return "Unauthorized action."

    # -------- PREVENT MODIFYING FINAL PLACEMENT --------
    if current_status == "Placed":
        conn.close()
        return "Placement is final and cannot be modified."

    # -------- IF MARKING AS PLACED --------
    if new_status == "Placed":

        # Mark selected application as Placed
        cursor.execute("""
            UPDATE Application
            SET status = 'Placed'
            WHERE id = ?
        """, (application_id,))

        # Reject all other applications of this student
        cursor.execute("""
            UPDATE Application
            SET status = 'Rejected'
            WHERE student_id = ?
            AND id != ?
            AND status != 'Placed'
        """, (student_id, application_id))

    else:
        # Normal status update
        cursor.execute("""
            UPDATE Application
            SET status = ?
            WHERE id = ?
        """, (new_status, application_id))

    conn.commit()
    conn.close()

    return redirect(url_for("company_dashboard"))

# ==================================================
# STUDENT SECTION
# ==================================================

@app.route("/student/register", methods=["GET", "POST"])
def student_register():

    if request.method == "POST":

        full_name = request.form.get("full_name")
        email = request.form.get("email")
        password = request.form.get("password")

        # -------- BASIC VALIDATION --------
        if not full_name or not email or not password:
            return "All fields are required."

        if len(password) < 6:
            return "Password must be at least 6 characters."

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO Student (
                    full_name,
                    email,
                    password_hash,
                    is_blacklisted
                )
                VALUES (?, ?, ?, 0)
            """, (full_name, email, hashed_password))

            conn.commit()
            conn.close()

            return redirect(url_for("student_login"))

        except sqlite3.IntegrityError:
            conn.close()
            return "Email already exists."

    return render_template("student_register.html")

@app.route("/student/login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, password_hash, is_blacklisted
            FROM Student
            WHERE email=?
        """, (email,))

        student = cursor.fetchone()
        conn.close()

        if not student:
            return "Invalid Credentials"

        student_id, stored_password, is_blacklisted = student


        print("Stored hash:", stored_password)
        print("Entered password:", password)
        print("Match:", check_password_hash(stored_password, password))

        if is_blacklisted == 1:
            return "Account Blacklisted"

        if not check_password_hash(stored_password, password):
            return "Invalid Credentials"

        session.clear()
        session["student_id"] = student_id

        print("Student session:", dict(session))

        return redirect(url_for("student_dashboard"))

    return render_template("student_login.html")

@app.route("/student/dashboard")
@student_required
def student_dashboard():

    student_id = session["student_id"]
    search = request.args.get("search", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    # -------- GET STUDENT NAME --------
    cursor.execute("SELECT full_name FROM Student WHERE id=?", (student_id,))
    student = cursor.fetchone()
    student_name = student["full_name"] if student else "Student"

    # -------- CHECK IF PLACED --------
    cursor.execute("""
        SELECT PlacementDrive.title,
               Company.name AS company_name
        FROM Application
        JOIN PlacementDrive ON Application.drive_id = PlacementDrive.id
        JOIN Company ON PlacementDrive.company_id = Company.id
        WHERE Application.student_id = ?
        AND Application.status = 'Placed'
    """, (student_id,))
    placement_info = cursor.fetchone()

    # -------- AVAILABLE DRIVES --------
    available_drives = []

    if not placement_info:

        base_query = """
            SELECT PlacementDrive.id,
                   PlacementDrive.title,
                   PlacementDrive.location,
                   PlacementDrive.required_skills,
                   PlacementDrive.deadline,
                   Company.name AS company_name
            FROM PlacementDrive
            JOIN Company ON PlacementDrive.company_id = Company.id
            WHERE PlacementDrive.approval_status = 'Approved'
            AND PlacementDrive.drive_status = 'Active'
            AND PlacementDrive.deadline >= DATE('now')
            AND PlacementDrive.id NOT IN (
                SELECT drive_id
                FROM Application
                WHERE student_id = ?
            )
        """

        params = [student_id]

        if search:
            base_query += """
                AND (
                    PlacementDrive.title LIKE ?
                    OR Company.name LIKE ?
                    OR PlacementDrive.required_skills LIKE ?
                    OR PlacementDrive.location LIKE ?
                )
            """
            params.extend([f"%{search}%"] * 4)

        base_query += " ORDER BY PlacementDrive.deadline ASC"

        cursor.execute(base_query, params)
        available_drives = cursor.fetchall()

    # -------- APPLIED DRIVES --------
    cursor.execute("""
        SELECT PlacementDrive.title,
               Company.name AS company_name,
               Application.status,
               Application.applied_at
        FROM Application
        JOIN PlacementDrive ON Application.drive_id = PlacementDrive.id
        JOIN Company ON PlacementDrive.company_id = Company.id
        WHERE Application.student_id = ?
        ORDER BY Application.applied_at DESC
    """, (student_id,))
    applied_drives = cursor.fetchall()

    # -------- NOTIFICATIONS --------
    cursor.execute("""
        SELECT id, message, created_at, is_read
        FROM Notification
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (student_id,))
    notifications = cursor.fetchall()

    conn.close()

    return render_template(
        "student_dashboard.html",
        student_name=student_name,
        available_drives=available_drives,
        applied_drives=applied_drives,
        placement_info=placement_info,
        notifications=notifications,
        search=search
    )

@app.route("/student/profile", methods=["GET", "POST"])
@student_required
def student_profile():

    student_id = session["student_id"]
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":

        # -------- GET FORM DATA --------
        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        degree = request.form.get("degree")
        branch = request.form.get("branch")
        college = request.form.get("college")
        cgpa = request.form.get("cgpa")
        skills = request.form.get("skills")

        # -------- UPDATE BASIC PROFILE FIELDS --------
        cursor.execute("""
            UPDATE Student
            SET full_name = ?,
                phone = ?,
                degree = ?,
                branch = ?,
                college = ?,
                cgpa = ?,
                skills = ?
            WHERE id = ?
        """, (
            full_name,
            phone,
            degree,
            branch,
            college,
            cgpa,
            skills,
            student_id
        ))

        # -------- HANDLE RESUME UPLOAD (SNAPSHOT SAFE) --------
        file = request.files.get("resume")

        if file and file.filename:

            # Get old resume name
            cursor.execute("SELECT resume_path FROM Student WHERE id=?", (student_id,))
            old_resume_row = cursor.fetchone()
            old_resume = old_resume_row["resume_path"] if old_resume_row else None

            # Save new resume first
            filename = secure_filename(file.filename)
            unique_name = str(uuid.uuid4()) + "_" + filename

            upload_folder = "uploads"
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            file.save(os.path.join(upload_folder, unique_name))

            # Update student resume_path
            cursor.execute("""
                UPDATE Student
                SET resume_path = ?
                WHERE id = ?
            """, (unique_name, student_id))

            # Delete old resume only if not referenced by any application
            if old_resume:
                cursor.execute("""
                    SELECT COUNT(*) FROM Application
                    WHERE resume_snapshot_path = ?
                """, (old_resume,))
                count = cursor.fetchone()[0]

                if count == 0:
                    old_path = os.path.join(upload_folder, old_resume)
                    if os.path.exists(old_path):
                        os.remove(old_path)

        conn.commit()

    # -------- FETCH UPDATED STUDENT DATA --------
    cursor.execute("SELECT * FROM Student WHERE id=?", (student_id,))
    student = cursor.fetchone()

    conn.close()

    return render_template("student_profile.html", student=student)



@app.route("/student/apply/<int:drive_id>", methods=["GET", "POST"])
@student_required
def apply_drive(drive_id):

    student_id = session["student_id"]
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # -------- BLOCK IF STUDENT ALREADY PLACED --------
    cursor.execute("""
        SELECT COUNT(*) FROM Application
        WHERE student_id = ?
        AND status = 'Placed'
    """, (student_id,))
    
    if cursor.fetchone()[0] > 0:
        conn.close()
        return "You are already placed and cannot apply."

    # -------- VALIDATE DRIVE --------
    cursor.execute("""
        SELECT PlacementDrive.*, Company.name AS company_name
        FROM PlacementDrive
        JOIN Company ON PlacementDrive.company_id = Company.id
        WHERE PlacementDrive.id = ?
        AND PlacementDrive.approval_status = 'Approved'
        AND PlacementDrive.drive_status = 'Active'
        AND PlacementDrive.deadline >= DATE('now')
    """, (drive_id,))
    
    drive = cursor.fetchone()

    if not drive:
        conn.close()
        return "Drive not available."

    # -------- CHECK STUDENT RESUME --------
    cursor.execute("SELECT resume_path FROM Student WHERE id=?", (student_id,))
    resume_row = cursor.fetchone()

    if not resume_row or not resume_row["resume_path"]:
        conn.close()
        return redirect(url_for("student_profile"))

    current_resume = resume_row["resume_path"]

    # -------- CHECK EXISTING APPLICATION --------
    cursor.execute("""
        SELECT * FROM Application
        WHERE student_id = ?
        AND drive_id = ?
    """, (student_id, drive_id))

    existing_application = cursor.fetchone()

    # -------- LOCK EDIT IF STATUS CHANGED --------
    if existing_application and existing_application["status"] != "Applied":
        conn.close()
        return "Application can no longer be edited."

    # -------- HANDLE FORM SUBMISSION --------
    if request.method == "POST":

        related_work = request.form.get("related_work")
        related_projects = request.form.get("related_projects")
        job_fit_statement = request.form.get("job_fit_statement")

        if not related_work or not related_projects or not job_fit_statement:
            conn.close()
            return "All fields are required."

        if existing_application:
            # UPDATE
            cursor.execute("""
                UPDATE Application
                SET related_work = ?,
                    related_projects = ?,
                    job_fit_statement = ?
                WHERE student_id = ?
                AND drive_id = ?
            """, (
                related_work,
                related_projects,
                job_fit_statement,
                student_id,
                drive_id
            ))
        else:
            # INSERT WITH RESUME SNAPSHOT
            cursor.execute("""
                INSERT INTO Application (
                    student_id,
                    drive_id,
                    resume_snapshot_path,
                    related_work,
                    related_projects,
                    job_fit_statement
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                student_id,
                drive_id,
                current_resume,
                related_work,
                related_projects,
                job_fit_statement
            ))

        conn.commit()
        conn.close()
        return redirect(url_for("student_dashboard"))

    conn.close()
    return render_template(
        "application_form.html",
        drive=drive,
        existing_application=existing_application
    )

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