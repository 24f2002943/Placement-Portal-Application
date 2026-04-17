from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
from flask import jsonify
import os
import uuid
import datetime
import shutil
from datetime import timedelta
from supabase import create_client, Client
import re
from dotenv import load_dotenv

def is_strong_password(password):
    # At least 6 chars, 1 uppercase, 1 number, 1 special character
    if len(password) < 6:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[\W_]", password):
        return False
    return True


app = Flask(__name__)
app.config["SECRET_KEY"] = "supersecretkey"

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=5)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "home"

app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"




def role_required(role):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            if not current_user.is_authenticated:
                return redirect(url_for("home"))

            if current_user.role != role:
                return "Unauthorized Access", 403

            return func(*args, **kwargs)

        return wrapper

    return decorator


SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



class User(UserMixin):

    def __init__(self,  user_id, role):
        self.id = str(user_id)
        self.role =  role

    def get_id(self):
        return f"{self.role}:{self.id}"
    
@login_manager.user_loader
def load_user(user_key):

    if not user_key or ":" not in user_key:
        return None

    role, user_id = user_key.split(":", 1)

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return None

    if role == "admin":
        response = supabase.table("admin").select("id").eq("id", user_id).execute()
        if response.data:
            return User(user_id, "admin")

    if role == "company":
        response = supabase.table("company").select("id").eq("id", user_id).execute()
        if response.data:
            return User(user_id, "company")

    if role == "student":
        response = supabase.table("student").select("id").eq("id", user_id).execute()
        if response.data:
            return User(user_id, "student")

    return None




ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


UPLOAD_FOLDER = "uploads/resumes"
ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

DB_NAME = "placement_portal.db"

from flask import send_from_directory

@app.route("/resume/<filename>")
@login_required
def download_resume(filename):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT resume_path FROM Student WHERE resume_path=?",
        (filename,)
    )

    file = cursor.fetchone()
    conn.close()

    if not file:
        return "File not found", 404

    return send_from_directory("uploads", filename)


@app.route("/")
def home():
    return "<h2>Placement Portal Running Successfully!</h2>"

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Enter username and password", "danger")
            return redirect(url_for("admin_login"))

        response = supabase.table("admin").select("*").eq("username", username).execute()
        admin = response.data[0] if response.data else None

        if not admin:
            flash("Invalid credentials", "danger")
            return redirect(url_for("admin_login"))

        if not check_password_hash(admin["password_hash"], password):
            flash("Invalid credentials", "danger")
            return redirect(url_for("admin_login"))

        user = User(admin["id"], "admin")
        login_user(user, remember=True)
        session.permanent = True

        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    
    if current_user.role != "admin":
        logout_user()
        return redirect(url_for("admin_login"))
     
    total_companies = supabase.table("company").select("id", count="exact").execute().count
    total_students = supabase.table("student").select("id", count="exact").execute().count
    total_jobs = supabase.table("placementdrive").select("id", count="exact").execute().count
    total_applications = supabase.table("application").select("id", count="exact").execute().count
    total_placements = supabase.table("placement").select("id", count="exact").execute().count

    admin_labels = ["Jobs", "Applications", "Placements"]
    admin_counts = [total_jobs, total_applications, total_placements]

    company_stats_res = supabase.rpc("get_company_stats").execute()
    # If RPC doesn't exist, we can fallback or implement it. 
    # For now, let's try to do it with client-side grouping if needed, 
    # but RPC is cleaner for SQL GROUP BY.
    # Let's check if I should implement the grouping here.
    
    # Actually, simpler to just fetch all and group in Python for now if schema is small
    # or use .select('approval_status') and then count.
    
    company_data = supabase.table("company").select("approval_status").execute().data
    company_counts_dict = {}
    for row in company_data:
        status = row["approval_status"]
        company_counts_dict[status] = company_counts_dict.get(status, 0) + 1
    
    company_labels = list(company_counts_dict.keys())
    company_counts = list(company_counts_dict.values())

    app_data = supabase.table("application").select("status").execute().data
    app_counts_dict = {}
    for row in app_data:
        status = row["status"]
        app_counts_dict[status] = app_counts_dict.get(status, 0) + 1
    
    application_labels = list(app_counts_dict.keys())
    application_counts = list(app_counts_dict.values())

    placement_rate = (
        round((total_placements / total_students) * 100, 2)
        if total_students else 0
    )

    return render_template(
        "admin_dashboard.html",
        companies=total_companies,
        students=total_students,
        jobs=total_jobs,
        applications=total_applications,
        placements=total_placements,
        placement_rate=placement_rate,
        admin_labels=admin_labels,
        admin_counts=admin_counts,
        company_labels=company_labels,
        company_counts=company_counts,
        application_labels=application_labels,
        application_counts=application_counts
    )


@app.route("/admin/manage_students")
@login_required
def manage_students():

    search_query = request.args.get("search", "").strip()

    if search_query:
        # Supabase 'or' logic for complex filters
        response = supabase.table("student").select("*").or_(
            f"full_name.ilike.%{search_query}%,email.ilike.%{search_query}%,phone.ilike.%{search_query}%"
        ).execute()
    else:
        response = supabase.table("student").select("*").execute()

    students = response.data
    return render_template(
        "manage_students.html",
        students=students,
        search_query=search_query
    )

@app.route("/admin/blacklist/student/<int:student_id>")
@login_required
def blacklist_student(student_id):

    # Use Supabase RPC (Stored Procedure) to demonstrate RDBMS features
    supabase.rpc("blacklist_student_with_cleanup", {"s_id": student_id}).execute()
    return redirect(url_for("manage_students"))




@app.route("/admin/manage_companies")
@login_required
def manage_companies():

    search_query = request.args.get("search", "").strip()

    if search_query:
        response = supabase.table("company").select("*").or_(
            f"name.ilike.%{search_query}%,email.ilike.%{search_query}%"
        ).execute()
    else:
        response = supabase.table("company").select("*").execute()

    companies = response.data
    return render_template("manage_companies.html",
                           companies=companies,
                           search_query=search_query)

@app.route("/admin/companies")
def admin_view_companies():

    response = supabase.table("company").select(
        "id, name, email, location, approval_status, is_blacklisted"
    ).order("approval_status").execute()

    companies = response.data
    return render_template("manage_companies.html", companies=companies)


@app.route("/admin/company/approve/<int:company_id>")
def approve_company(company_id):

    supabase.table("company").update({
        "approval_status": "Approved"
    }).eq("id", company_id).execute()

    flash("Company Approved Successfully!", "success")
    return redirect(url_for("admin_view_companies"))

@app.route("/admin/company/reject/<int:company_id>")
def reject_company(company_id):

    supabase.table("company").update({
        "approval_status": "Rejected"
    }).eq("id", company_id).execute()

    flash("Company Rejected!", "danger")
    return redirect(url_for("admin_view_companies"))


@app.route("/admin/blacklist/company/<int:company_id>")
@login_required
def blacklist_company(company_id):

    supabase.table("company").update({"is_blacklisted": 1}).eq("id", company_id).execute()
    return redirect(url_for("manage_companies"))


@app.route("/admin/manage_jobs")
@login_required
def manage_jobs():

    search_query = request.args.get("search", "").strip()

    if search_query:
        # Supabase join: select fields from PlacementDrive and name from Company
        response = supabase.table("placementdrive").select(
            "*, company(name)"
        ).or_(
            f"title.ilike.%{search_query}%,location.ilike.%{search_query}%,company.name.ilike.%{search_query}%"
        ).execute()

    else:
        response = supabase.table("placementdrive").select(
            "*, company(name)"
        ).execute()

    jobs = response.data
    return render_template(
        "manage_jobs.html",
        jobs=jobs,
        search_query=search_query
    )


@app.route("/admin/job/<int:drive_id>/<string:action>")
@login_required
def update_job_status(drive_id, action):

    if action == "approve":
        supabase.table("placementdrive").update({"approval_status": "Approved"}).eq("id", drive_id).execute()
    elif action == "reject":
        supabase.table("placementdrive").update({"approval_status": "Rejected"}).eq("id", drive_id).execute()

    return redirect(url_for("manage_jobs"))


@app.route("/admin/manage_applications")
@login_required
def manage_applications():

    search_query = request.args.get("search", "").strip()

    if search_query:
        response = supabase.table("application").select(
            "id, status, student(full_name), placementdrive(title)"
        ).or_(
            f"student.full_name.ilike.%{search_query}%,placementdrive.title.ilike.%{search_query}%"
        ).execute()

    else:
        response = supabase.table("application").select(
            "id, status, student(full_name), placementdrive(title)"
        ).execute()

    # Flatten for template compatibility if needed
    applications = []
    for app in response.data:
        applications.append({
            "id": app["id"],
            "status": app["status"],
            "student_name": app["student"]["full_name"],
            "drive_title": app["placementdrive"]["title"]
        })

    return render_template(
        "manage_applications.html",
        applications=applications,
        search_query=search_query
    )





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

        if not is_strong_password(password):
            flash("Password must be at least 6 characters, include 1 uppercase, 1 number, and 1 special character.", "danger")
            return redirect(url_for("company_register"))

        if "@" not in email:
            flash("Invalid email format.", "danger")
            return redirect(url_for("company_register"))
        
        response = supabase.table("company").select("id").eq("email", email).execute()
        if response.data:
            flash("Email already registered.", "warning")
            return redirect(url_for("company_register"))

        hashed_password = generate_password_hash(password)

        supabase.table("company").insert({
            "name": name,
            "email": email,
            "password_hash": hashed_password,
            "location": location,
            "industry": industry,
            "approval_status": "Pending",
            "is_blacklisted": 0
        }).execute()

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

        response = supabase.table("company").select("*").eq("email", email).execute()
        company = response.data[0] if response.data else None

        if not company:
            flash("Invalid email or password.", "danger")
            return redirect(url_for("company_login"))

        if company["is_blacklisted"] == 1:
            flash("Your company account has been blacklisted.", "danger")
            return redirect(url_for("company_login"))

        if company["approval_status"] == "Pending":
            flash("Your account is pending admin approval.", "warning")
            return redirect(url_for("company_login"))

        if company["approval_status"] == "Rejected":
            flash("Your registration was rejected by admin.", "danger")
            return redirect(url_for("company_login"))

        if not check_password_hash(company["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("company_login"))


        supabase.table("company").update({
            "updated_at": datetime.datetime.utcnow().isoformat()
        }).eq("id", company["id"]).execute()

        user = User(company["id"], "company")
        login_user(user, remember=True)
        session.permanent = True

        flash("Login successful!", "success")
        return redirect(url_for("company_dashboard"))

    return render_template("company_login.html")


@app.route("/company/dashboard")
@login_required
def company_dashboard():
    

    if current_user.role != "company":
        return redirect(url_for("company_login"))

    company_id = int(current_user.id)
    filter_type = request.args.get("filter")

    total_jobs = supabase.table("placementdrive").select("id", count="exact").eq("company_id", company_id).execute().count
    active_jobs = supabase.table("placementdrive").select("id", count="exact").eq("company_id", company_id).eq("drive_status", "Active").execute().count
    closed_jobs = supabase.table("placementdrive").select("id", count="exact").eq("company_id", company_id).eq("drive_status", "Closed").execute().count
    
    total_applications = supabase.table("application").select(
        "id", count="exact"
    ).eq("placementdrive.company_id", company_id).execute().count 
    # Wait, the above join in count is tricky. Let's fetch the drive IDs for this company first.
    
    company_drives = supabase.table("placementdrive").select("id").eq("company_id", company_id).execute()
    drive_ids = [d["id"] for d in company_drives.data]
    
    if drive_ids:
        total_applications = supabase.table("application").select("id", count="exact").in_("drive_id", drive_ids).execute().count
    else:
        total_applications = 0

    if filter_type == "applications":
        return redirect(url_for("view_company_applications"))    

    query = supabase.table("placementdrive").select("*, application(id)").eq("company_id", company_id)

    if filter_type == "active":
        query = query.eq("drive_status", "Active")
    elif filter_type == "closed":
        query = query.eq("drive_status", "Closed")

    jobs_res = query.order("id", desc=True).execute()
    jobs_data = jobs_res.data
    
    # Process jobs to include total_applications count
    jobs = []
    for job in jobs_data:
        job["total_applications"] = len(job.get("application", []))
        jobs.append(job)

    # Statistics for charts
    drive_chart = []
    for job in jobs:
        drive_chart.append({
            "title": job["title"],
            "total": job["total_applications"]
        })
    
    # Calculate percentages for drive chart
    max_apps = max([d["total"] for d in drive_chart], default=1)
    for d in drive_chart:
        d["percent"] = round((d["total"] / max_apps) * 100, 2) if max_apps else 0

    # Status statistics
    status_counts_dict = {}
    if drive_ids:
        app_res = supabase.table("application").select("status").in_("drive_id", drive_ids).execute()
        for app in app_res.data:
            s = app["status"]
            status_counts_dict[s] = status_counts_dict.get(s, 0) + 1
            
    status_chart = []
    max_status = max(status_counts_dict.values(), default=1)
    for s, c in status_counts_dict.items():
        status_chart.append({
            "status": s,
            "count": c,
            "percent": round((c / max_status) * 100, 2) if max_status else 0
        })

    return render_template(
        "company_dashboard.html",
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        closed_jobs=closed_jobs,
        total_applications=total_applications,
        jobs=jobs,
        drive_chart=drive_chart,
        status_chart=status_chart,
        filter_type=filter_type
    )

@app.route("/company/post_drive", methods=["GET", "POST"])
@login_required
def post_drive():

    company_id = int(current_user.id)

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        location = request.form["location"]
        required_skills = request.form["required_skills"]
        experience_required = request.form["experience_required"]
        min_salary = request.form["min_salary"]
        max_salary = request.form["max_salary"]
        deadline = request.form["deadline"]




        if not title or not location or not deadline:
            flash("Title, Location and Deadline are required.", "danger")
            return redirect(url_for("post_drive"))

        if int(min_salary) > int(max_salary):
            flash("Minimum salary cannot exceed maximum salary.", "danger")
            return redirect(url_for("post_drive"))

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
@login_required
def view_job_applications(drive_id):

    if current_user.role != "company":
        return redirect(url_for("company_login"))

    company_id = int(current_user.id)

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
           Application.related_work,
           Application.related_projects,
           Application.job_fit_statement,
           Student.id AS student_id,
           Student.full_name,
           Student.email,
           Student.phone,
           Application.resume_snapshot_path
    FROM Application
    JOIN Student
    ON Application.student_id = Student.id
    WHERE Application.drive_id = ?
""", (drive_id,))

    applications = cursor.fetchall()

    conn.close()

    return render_template(
        "view_applications.html",
        job=job,
        applications=applications
    )


@app.route("/company/drive/<int:drive_id>/toggle")
@login_required
def toggle_drive_status(drive_id):

    company_id = int(current_user.id)

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()


    cursor.execute("""
        SELECT *
        FROM PlacementDrive
        WHERE id=? AND company_id=?
    """, (drive_id, company_id))

    drive = cursor.fetchone()

    if not drive:
        conn.close()
        return "Unauthorized action"

    
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
@login_required
def update_application_status(application_id, new_status):

    company_id = int(current_user.id)
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

    if current_user.role != "company":
        return redirect(url_for("company_login"))

    company_id = int(current_user.id)
    new_status = request.form.get("status")

    if new_status not in ["Applied", "Shortlisted", "Interview", "Rejected", "Placed"]:
        return "Invalid status."

    response = supabase.table("application").select(
        "student_id, status, placementdrive(company_id)"
    ).eq("id", application_id).execute()

    if not response.data:
        return "Application not found."

    row = response.data[0]
    student_id = row["student_id"]
    current_status = row["status"]
    drive_company_id = row["placementdrive"]["company_id"]

    if drive_company_id != company_id:
        return "Unauthorized action."

    if current_status == "Placed":
        return "Placement is final and cannot be modified."

    if new_status == "Placed":
        # Finalize placement
        supabase.table("application").update({"status": "Placed"}).eq("id", application_id).execute()
        
        # Reject other applications for the same student
        supabase.table("application").update({"status": "Rejected"}).eq("student_id", student_id).neq("id", application_id).neq("status", "Placed").execute()

    else:
        supabase.table("application").update({"status": new_status}).eq("id", application_id).execute()

    return redirect(url_for("company_dashboard"))



@app.route("/student/register", methods=["GET", "POST"])
def student_register():
    if request.method == "POST":

        full_name = request.form.get("full_name","").strip()
        email = request.form.get("email","").strip()
        password = request.form.get("password","")

        if not full_name or not email or not password:
            return "All fields are required."

        if len(full_name) < 3:
            return "Name must be at least 3 characters."

        if "@" not in email:
            return "Invalid email address."

        if not is_strong_password(password):
            return "Password must be at least 6 characters, include 1 uppercase, 1 number, and 1 special character."

        hashed_password = generate_password_hash(password)

        response = supabase.table("student").select("id").eq("email", email).execute()
        if response.data:
            return "Email already exists."

        supabase.table("student").insert({
            "full_name": full_name,
            "email": email,
            "password_hash": hashed_password,
            "is_blacklisted": 0
        }).execute()

        return redirect(url_for("student_login"))

    return render_template("student_register.html")

@app.route("/student/login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        response = supabase.table("student").select("*").eq("email", email).execute()
        student = response.data[0] if response.data else None

        if not student:
            return "Invalid Credentials"

        if student["is_blacklisted"] == 1:
            return "Account Blacklisted"

        if not check_password_hash(student["password_hash"], password):
            return "Invalid Credentials"

        user = User(student["id"], "student")
        login_user(user, remember=True)
        session.permanent = True

        return redirect(url_for("student_dashboard"))

    return render_template("student_login.html")


@app.route("/student/dashboard")
@login_required
def student_dashboard():
    
    if current_user.role != "student":
        return redirect(url_for("student_login"))
    
    student_id = int(current_user.id)
    search = request.args.get("search", "").strip()

    # Get student name
    student_res = supabase.table("student").select("full_name").eq("id", student_id).execute()
    student_name = student_res.data[0]["full_name"] if student_res.data else "Student"

    # Get placement info
    placement_res = supabase.table("application").select(
        "placementdrive(title), placementdrive(company(name))"
    ).eq("student_id", student_id).eq("status", "Placed").limit(1).execute()
    
    placement_info = None
    if placement_res.data:
        p = placement_res.data[0]
        placement_info = {
            "title": p["placementdrive"]["title"],
            "company_name": p["placementdrive"]["company"]["name"]
        }

    # Available drives logic
    available_drives = []
    if not placement_info:
        # Get applied drive IDs
        applied_res = supabase.table("application").select("drive_id").eq("student_id", student_id).execute()
        applied_ids = [a["drive_id"] for a in applied_res.data]


        now = datetime.date.today().isoformat()

        query = supabase.table("placementdrive").select(
            "*, company(name)"
        ).eq("approval_status", "Approved").eq("drive_status", "Active").gte("deadline", now)

        if applied_ids:
            query = query.not_.in_("id", applied_ids)

        if search:
            query = query.or_(
                f"title.ilike.%{search}%,company.name.ilike.%{search}%,required_skills.ilike.%{search}%,location.ilike.%{search}%"
            )

        drives_res = query.order("deadline", asc=True).execute()
        available_drives = drives_res.data

    # Applied drives
    applied_drives_res = supabase.table("application").select(
        "placementdrive(title), placementdrive(company(name)), status, applied_at"
    ).eq("student_id", student_id).order("applied_at", desc=True).execute()
    
    applied_drives = []
    for app in applied_drives_res.data:
        applied_drives.append({
            "title": app["placementdrive"]["title"],
            "company_name": app["placementdrive"]["company"]["name"],
            "status": app["status"],
            "applied_at": app["applied_at"]
        })
    
    # Status counts for chart
    app_stats_res = supabase.table("application").select("status").eq("student_id", student_id).execute()
    status_counts_dict = {}
    for app in app_stats_res.data:
        s = app["status"]
        status_counts_dict[s] = status_counts_dict.get(s, 0) + 1
    
    status_labels = list(status_counts_dict.keys())
    status_counts = list(status_counts_dict.values())

    return render_template(
        "student_dashboard.html",
        student_name=student_name,
        available_drives=available_drives,
        applied_drives=applied_drives,
        placement_info=placement_info,
        status_labels=status_labels,
        status_counts=status_counts,
        search=search
    )
 




@app.route("/student/profile", methods=["GET", "POST"])
@login_required
def student_profile():

    student_id = int(current_user.id)
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":

        
        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        degree = request.form.get("degree")
        branch = request.form.get("branch")
        college = request.form.get("college")
        cgpa = request.form.get("cgpa")
        skills = request.form.get("skills")

        supabase.table("student").update({
            "full_name": full_name,
            "phone": phone,
            "degree": degree,
            "branch": branch,
            "college": college,
            "cgpa": cgpa,
            "skills": skills
        }).eq("id", student_id).execute()

        
        file = request.files.get("resume")

        if file:
            if file.filename == "":
                flash("No file selected.", "danger")
                return redirect(url_for("student_profile"))

            if not allowed_file(file.filename):
                flash("Only PDF files are allowed.", "danger")
                return redirect(url_for("student_profile"))

            res = supabase.table("student").select("resume_path").eq("id", student_id).execute()
            old_resume = res.data[0]["resume_path"] if res.data else None

            filename = secure_filename(file.filename)
            unique_name = str(uuid.uuid4()) + "_" + filename

            # --- Supabase Storage Upload ---
            file_content = file.read()
            supabase.storage.from_("resumes").upload(unique_name, file_content, {"content-type": "application/pdf"})
            # -------------------------------

            supabase.table("student").update({
                "resume_path": unique_name
            }).eq("id", student_id).execute()

            if old_resume:
                # Optional: Delete old resume from cloud
                try:
                    supabase.storage.from_("resumes").remove([old_resume])
                except:
                    pass

    res = supabase.table("student").select("*").eq("id", student_id).execute()
    student = res.data[0] if res.data else None
    return render_template("student_profile.html", student=student)



@app.route("/student/apply/<int:drive_id>", methods=["GET", "POST"])
@login_required
def apply_drive(drive_id):

    student_id = int(current_user.id)

    # check if already placed
    placed_res = supabase.table("application").select("id", count="exact").eq("student_id", student_id).eq("status", "Placed").execute()
    if placed_res.count > 0:
        return "You are already placed and cannot apply."

    # get drive info
    import datetime
    now = datetime.date.today().isoformat()
    drive_res = supabase.table("placementdrive").select(
        "*, company(name)"
    ).eq("id", drive_id).eq("approval_status", "Approved").eq("drive_status", "Active").gte("deadline", now).execute()
    
    drive = drive_res.data[0] if drive_res.data else None
    if not drive:
        return "Drive not available."

    # get student's current resume
    student_res = supabase.table("student").select("resume_path").eq("id", student_id).execute()
    current_resume = student_res.data[0]["resume_path"] if student_res.data else None

    if not current_resume:
        return redirect(url_for("student_profile"))

    # check if already applied
    existing_res = supabase.table("application").select("*").eq("student_id", student_id).eq("drive_id", drive_id).execute()
    existing_application = existing_res.data[0] if existing_res.data else None

    if existing_application and existing_application["status"] != "Applied":
        return "Application can no longer be edited."

    if request.method == "POST":
        related_work = request.form.get("related_work")
        related_projects = request.form.get("related_projects")
        job_fit_statement = request.form.get("job_fit_statement")

        if not related_work or not related_projects or not job_fit_statement:
            return "All fields are required."

        if existing_application:
            supabase.table("application").update({
                "related_work": related_work,
                "related_projects": related_projects,
                "job_fit_statement": job_fit_statement
            }).eq("student_id", student_id).eq("drive_id", drive_id).execute()

        else:
            # ---------- RESUME SNAPSHOT (CLOUD COPY) ----------
            snapshot_name = "snapshot_" + (current_resume or "unknown")
            try:
                supabase.storage.from_("resumes").copy(current_resume, snapshot_name)
            except:
                snapshot_name = current_resume # Fallback if copy fails
            # --------------------------------------------------

            supabase.table("application").insert({
                "student_id": student_id,
                "drive_id": drive_id,
                "resume_snapshot_path": snapshot_name,
                "related_work": related_work,
                "related_projects": related_projects,
                "job_fit_statement": job_fit_statement
            }).execute()

        return redirect(url_for("student_dashboard"))

    return render_template(
        "application_form.html",
        drive=drive,
        existing_application=existing_application
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("home"))



    response = supabase.table("student").select("id, full_name, email, degree, branch").execute()
    return jsonify(response.data)


@app.route("/api/students/<int:student_id>", methods=["GET"])
def api_get_student(student_id):
    response = supabase.table("student").select("*").eq("id", student_id).execute()
    if not response.data:
        return jsonify({"error": "Student not found"}), 404

    return jsonify(response.data[0])


@app.route("/api/students", methods=["POST"])
def api_create_student():
    data = request.get_json()
    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")

    if not full_name or not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    hashed_password = generate_password_hash(password)

    # Check for existing email
    exists_res = supabase.table("student").select("id").eq("email", email).execute()
    if exists_res.data:
        return jsonify({"error": "Email already exists"}), 400

    supabase.table("student").insert({
        "full_name": full_name,
        "email": email,
        "password_hash": hashed_password,
        "is_blacklisted": 0
    }).execute()

    return jsonify({"message": "Student created"}), 201

@app.route("/api/students/<int:student_id>", methods=["PUT"])
def api_update_student(student_id):
    data = request.get_json()
    
    supabase.table("student").update({
        "full_name": data.get("full_name"),
        "phone": data.get("phone"),
        "degree": data.get("degree"),
        "branch": data.get("branch"),
        "college": data.get("college"),
        "cgpa": data.get("cgpa"),
        "skills": data.get("skills")
    }).eq("id", student_id).execute()

    return jsonify({"message": "Student updated"})


@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def api_delete_student(student_id):
    supabase.table("student").delete().eq("id", student_id).execute()
    return jsonify({"message": "Student deleted"})


@app.route("/api/drives", methods=["GET"])
def api_get_drives():
    status = request.args.get("status")
    location = request.args.get("location")
    search = request.args.get("search")

    query = supabase.table("placementdrive").select(
        "id, title, location, required_skills, approval_status, drive_status"
    ).eq("approval_status", "Approved")

    if status:
        query = query.eq("drive_status", status)

    if location:
        query = query.ilike("location", f"%{location}%")

    if search:
        query = query.or_(f"title.ilike.%{search}%,required_skills.ilike.%{search}%")

    response = query.execute()
    return jsonify(response.data)


@app.route("/api/applications", methods=["GET"])
def api_get_applications():
    response = supabase.table("application").select(
        "id, status, student(full_name), placementdrive(title)"
    ).execute()

    # Flatten for JSON response
    output = []
    for app in response.data:
        output.append({
            "id": app["id"],
            "status": app["status"],
            "full_name": app["student"]["full_name"],
            "title": app["placementdrive"]["title"]
        })

    return jsonify(output)

if __name__ == "__main__":
    app.run(debug=True)