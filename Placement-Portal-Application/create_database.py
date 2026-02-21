import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "placement_portal.db"


def create_tables():
    """
    This function initializes the complete database schema
    for the Placement Portal system.
    """

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Enable foreign key enforcement
    cursor.execute("PRAGMA foreign_keys = ON;")

    # ---------------- ADMIN TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)

    # ---------------- COMPANY TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Company (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        approval_status TEXT DEFAULT 'Pending',
        is_blacklisted INTEGER DEFAULT 0
    );
    """)

    # ---------------- STUDENT TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Student (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_blacklisted INTEGER DEFAULT 0
    );
    """)

    # ---------------- OPPORTUNITY TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Opportunity (
        opportunity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        posted_by_company INTEGER NOT NULL,
        role_title TEXT NOT NULL,
        role_description TEXT NOT NULL,
        job_location TEXT NOT NULL,
        offered_ctc TEXT NOT NULL,
        created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (posted_by_company)
            REFERENCES Company(id)
            ON DELETE CASCADE
    );
    """)

    # ---------------- APPLICATION TRACKER TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ApplicationTracker (
        application_id INTEGER PRIMARY KEY AUTOINCREMENT,
        applicant_student INTEGER NOT NULL,
        related_opportunity INTEGER NOT NULL,
        current_status TEXT DEFAULT 'Under Review',
        applied_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (applicant_student)
            REFERENCES Student(id)
            ON DELETE CASCADE,

        FOREIGN KEY (related_opportunity)
            REFERENCES Opportunity(opportunity_id)
            ON DELETE CASCADE,

        UNIQUE(applicant_student, related_opportunity)
    );
    """)

    # ---------------- DEFAULT ADMIN INSERT ----------------
    cursor.execute("SELECT * FROM Admin WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO Admin (username, password_hash)
        VALUES (?, ?)
        """, ("admin", generate_password_hash("admin123")))
    # Insert sample company if not exists
    cursor.execute("SELECT * FROM Company WHERE email = ?", ("testcompany@gmail.com",))
    if not cursor.fetchone():
       cursor.execute("""
       INSERT INTO Company (name, email, password_hash, approval_status)
       VALUES (?, ?, ?, ?)
       """, ("Test Company", "testcompany@gmail.com", generate_password_hash("1234"), "Approved"))

    # Get company ID
    cursor.execute("SELECT id FROM Company WHERE email = ?", ("testcompany@gmail.com",))
    company_id = cursor.fetchone()[0]

    # Insert sample opportunity
    cursor.execute("""
    INSERT INTO Opportunity (
        posted_by_company,
        role_title,
        role_description,
        job_location,
        offered_ctc
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        company_id,
        "Backend Developer",
        "Looking for Python + Flask developer",
        "Bangalore",
        "8 LPA"
    ))


    # ---------------- PLACEMENT TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Placement (
        placement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        related_application INTEGER NOT NULL UNIQUE,
        offer_package TEXT NOT NULL,
        joining_date DATE,
        placement_status TEXT DEFAULT 'Confirmed',

        FOREIGN KEY (related_application)
            REFERENCES ApplicationTracker(application_id)
            ON DELETE CASCADE
    );
    """)
    connection.commit()
    connection.close()

    print("✅ Database and all tables created successfully!")


if __name__ == "__main__":
    create_tables()