from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "placement_portal.db"


# ---------------- HOME ----------------
@app.route("/")
def home():
    return "<h2>Placement Portal Running Successfully!</h2>"


# ---------------- ADMIN LOGIN ----------------
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


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    return "<h2>Welcome Admin! Login Successful 🎉</h2>"


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin_login"))


# ---------------- COMPANY REGISTER ----------------
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
                INSERT INTO Company (name, email, password_hash)
                VALUES (?, ?, ?)
            """, (name, email, hashed_password))
            conn.commit()
            conn.close()
            return "Registration Successful! Wait for Admin Approval."
        except:
            conn.close()
            return "Email already exists!"

    return render_template("company_register.html")


# ---------------- COMPANY LOGIN ----------------
@app.route("/company/login", methods=["GET", "POST"])
def company_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, password_hash, approval_status, is_blacklisted 
            FROM Company WHERE email = ?
        """, (email,))
        company = cursor.fetchone()
        conn.close()

        if company:
            company_id, stored_password, approval_status, is_blacklisted = company

            if is_blacklisted:
                return "You are blacklisted by Admin."

            if approval_status != "Approved":
                return "Your account is not approved yet."

            if check_password_hash(stored_password, password):
                session["company"] = company_id
                return redirect(url_for("company_dashboard"))

        return "Invalid Credentials"

    return render_template("company_login.html")


# ---------------- COMPANY DASHBOARD ----------------
@app.route("/company/dashboard")
def company_dashboard():
    if "company" not in session:
        return redirect(url_for("company_login"))

    return "<h2>Welcome Company! Login Successful 🎉</h2>"


# ---------------- STUDENT REGISTER ----------------
@app.route("/student/register", methods=["GET", "POST"])
def student_register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not full_name or not email or not password:
            return "All fields are required!"

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO Student (full_name, email, password_hash)
                VALUES (?, ?, ?)
            """, (full_name, email, hashed_password))
            conn.commit()
            conn.close()
            return "Student Registration Successful!"
        except sqlite3.IntegrityError:
            conn.close()
            return "Email already exists!"

    return render_template("student_register.html")


# ---------------- STUDENT LOGIN ----------------
@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

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
        else:
            return "Invalid Credentials"

    return render_template("student_login.html")
# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student/dashboard")
def student_dashboard():
    if "student" not in session:
        return redirect(url_for("student_login"))

    return render_template("student_dashboard.html")


# ---------------- VIEW OPPORTUNITIES ----------------
@app.route("/student/opportunities")
def view_opportunities():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM Opportunity")
    opportunities = cursor.fetchall()

    connection.close()

    return render_template("student_opportunities.html", opportunities=opportunities)

# ---------------- APPLY TO OPPORTUNITY ----------------
@app.route("/student/apply/<int:opportunity_id>")
def apply_opportunity(opportunity_id):

    if "student" not in session:
        return redirect(url_for("student_login"))

    student_id = session["student"]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM ApplicationTracker
        WHERE applicant_student = ? AND related_opportunity = ?
    """, (student_id, opportunity_id))

    existing_application = cursor.fetchone()

    if existing_application:
        conn.close()
        return "You have already applied to this opportunity."

    cursor.execute("""
        INSERT INTO ApplicationTracker
        (applicant_student, related_opportunity)
        VALUES (?, ?)
    """, (student_id, opportunity_id))

    conn.commit()
    conn.close()

    return "Application Submitted Successfully!"

# ---------------- ADD SAMPLE JOB (TEMPORARY) ----------------
@app.route("/add_sample_job")
def add_sample_job():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO Opportunity 
        (posted_by_company, role_title, role_description, job_location, offered_ctc)
        VALUES (?, ?, ?, ?, ?)
    """, (1, "Software Developer", "Python + Flask Developer", "Pune", "6 LPA"))

    connection.commit()
    connection.close()

    return "Sample Job Added Successfully!"
# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)

