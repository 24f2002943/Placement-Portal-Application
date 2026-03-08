import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "placement_portal.db"
# TODO:
# Add industry column to Company
# Add proper upcoming/past filtering in admin manage jobs
# Update search to include industry + student id

def create_tables():
    connection = sqlite3.connect(DB_NAME)
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.cursor()

    # ---------------- ADMIN TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)

    cursor.execute("SELECT id FROM Admin WHERE username = ?", ("admin",))
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
        phone TEXT,
        website TEXT,
        location TEXT,
        description TEXT,
        industry TEXT,
 
        approval_status TEXT DEFAULT 'Pending'
            CHECK(approval_status IN ('Pending','Approved','Rejected')),

        is_blacklisted INTEGER DEFAULT 0
            CHECK(is_blacklisted IN (0,1)),

        approved_by INTEGER,
        approved_date DATETIME,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (approved_by)
            REFERENCES Admin(id)
            ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS update_company_timestamp
    AFTER UPDATE ON Company
    FOR EACH ROW
    BEGIN
        UPDATE Company
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = OLD.id;
    END;
    """)

    # ---------------- STUDENT TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Student (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        phone TEXT,
        degree TEXT,
        branch TEXT,
        college TEXT,
        cgpa REAL,
        skills TEXT,
        resume_path TEXT,

        is_blacklisted INTEGER DEFAULT 0
            CHECK(is_blacklisted IN (0,1)),

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS update_student_timestamp
    AFTER UPDATE ON Student
    FOR EACH ROW
    BEGIN
        UPDATE Student
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = OLD.id;
    END;
    """)

    # ---------------- PLACEMENT DRIVE TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS PlacementDrive (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,

        title TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT NOT NULL,
        required_skills TEXT NOT NULL,
        experience_required TEXT NOT NULL,

        min_salary INTEGER,
        max_salary INTEGER,
        deadline DATE,

        approval_status TEXT DEFAULT 'Pending'
            CHECK(approval_status IN ('Pending','Approved','Rejected')),

        drive_status TEXT DEFAULT 'Active'
            CHECK(drive_status IN ('Active','Closed')),

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (company_id)
            REFERENCES Company(id)
            ON DELETE CASCADE
    );
    """)




    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS update_drive_timestamp
    AFTER UPDATE ON PlacementDrive
    FOR EACH ROW
    BEGIN
        UPDATE PlacementDrive
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = OLD.id;
    END;
    """)

   #------------- APPLICATION TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Application (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student_id INTEGER NOT NULL,
        drive_id INTEGER NOT NULL,
                   
        -- Resume snapshot (CRITICAL ADDITION)
        resume_snapshot_path TEXT NOT NULL,

        -- Student Answers (Application Form)
        related_work TEXT NOT NULL,
        related_projects TEXT NOT NULL,
        job_fit_statement TEXT NOT NULL,

        --  status Tracking
        status TEXT NOT NULL DEFAULT 'Applied'
            CHECK(status IN (
                'Applied',
                'Shortlisted',
                'Interview',
                'Rejected',
                'Placed'
            )),

        -- Timestamps
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,

        -- Notification tracking
        last_seen_status TEXT DEFAULT 'Applied',

        -- Foreign Keys
        FOREIGN KEY (student_id)
            REFERENCES Student(id)
            ON DELETE CASCADE,

        FOREIGN KEY (drive_id)
            REFERENCES PlacementDrive(id)
            ON DELETE CASCADE,

        -- Prevent duplicate applications
        UNIQUE(student_id, drive_id)
    );
    """)
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS update_application_timestamp
    AFTER UPDATE ON Application
    FOR EACH ROW
    BEGIN
        UPDATE Application
        SET last_updated = CURRENT_TIMESTAMP
        WHERE id = NEW.id;
    END;
    """)

    
    # ---------------- PLACEMENT TABLE ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Placement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        application_id INTEGER NOT NULL UNIQUE,
        offer_package TEXT,
        joining_date DATE,

        placement_status TEXT DEFAULT 'Confirmed'
            CHECK(placement_status IN ('Confirmed','Joined','Declined')),

        placed_at DATETIME DEFAULT CURRENT_TIMESTAMP,

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