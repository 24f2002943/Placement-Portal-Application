import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "placement_portal.db"


def create_tables():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Enable Foreign Keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # ---------------- ADMIN TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)

    # Insert Default Admin
    cursor.execute("SELECT * FROM Admin WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO Admin (username, password_hash)
        VALUES (?, ?)
        """, ("admin", generate_password_hash("admin123")))

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

    # ---------------- JOB POSITION TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS JobPosition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT NOT NULL,
        ctc TEXT NOT NULL,
        deadline TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id)
            REFERENCES Company(id)
            ON DELETE CASCADE
    );
    """)

    # ---------------- APPLICATION TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Application (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,

        status TEXT DEFAULT 'Pending'
            CHECK(status IN ('Pending', 'Shortlisted', 'Selected', 'Rejected')),

        applied_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (student_id)
            REFERENCES Student(id)
            ON DELETE CASCADE,

        FOREIGN KEY (job_id)
            REFERENCES JobPosition(id)
            ON DELETE CASCADE,

        UNIQUE(student_id, job_id)
    );
    """)

    # Create index for faster queries
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_application_student
    ON Application(student_id);
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_application_job
    ON Application(job_id);
    """)

    # ---------------- PLACEMENT TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Placement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL UNIQUE,
        offer_package TEXT NOT NULL,
        joining_date DATE,
        placement_status TEXT DEFAULT 'Confirmed',

        FOREIGN KEY (application_id)
            REFERENCES Application(id)
            ON DELETE CASCADE
    );
    """)

    connection.commit()
    connection.close()

    print("✅ Database and all tables created successfully!")


if __name__ == "__main__":
    create_tables()