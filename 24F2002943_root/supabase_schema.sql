-- Supabase Postgres Schema for Placement Portal

-- Enable UUID extension if we ever need it
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------- ADMIN TABLE ----------------
CREATE TABLE Admin (
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL
);

-- Insert admin user (password 'admin123' hashed with werkzeug default method)
-- Note: You may need to replace this hash with a freshly generated one from Python if it doesn't match
INSERT INTO Admin (username, password_hash)
VALUES ('admin', 'scrypt:32768:8:1$y6X8U2QjV9Z1$7...placeholder...'); 
-- For data migration, we'll sync the real hash from SQLite anyway.

-- ---------------- COMPANY TABLE ----------------
CREATE TABLE Company (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    phone VARCHAR,
    website VARCHAR,
    location VARCHAR,
    description TEXT,
    industry VARCHAR,
    
    approval_status VARCHAR DEFAULT 'Pending'
        CHECK (approval_status IN ('Pending','Approved','Rejected')),

    is_blacklisted INTEGER DEFAULT 0
        CHECK (is_blacklisted IN (0,1)),

    approved_by INTEGER REFERENCES Admin(id) ON DELETE SET NULL,
    approved_date TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------- STUDENT TABLE ----------------
CREATE TABLE Student (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    phone VARCHAR,
    degree VARCHAR,
    branch VARCHAR,
    college VARCHAR,
    cgpa REAL,
    skills TEXT,
    resume_path VARCHAR,

    is_blacklisted INTEGER DEFAULT 0
        CHECK (is_blacklisted IN (0,1)),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------- PLACEMENT DRIVE TABLE ----------------
CREATE TABLE PlacementDrive (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES Company(id) ON DELETE CASCADE,

    title VARCHAR NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR NOT NULL,
    required_skills TEXT NOT NULL,
    experience_required VARCHAR NOT NULL,

    min_salary INTEGER,
    max_salary INTEGER,
    deadline DATE,

    approval_status VARCHAR DEFAULT 'Pending'
        CHECK (approval_status IN ('Pending','Approved','Rejected')),

    drive_status VARCHAR DEFAULT 'Active'
        CHECK (drive_status IN ('Active','Closed')),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------- APPLICATION TABLE ----------------
CREATE TABLE Application (
    id SERIAL PRIMARY KEY,

    student_id INTEGER NOT NULL REFERENCES Student(id) ON DELETE CASCADE,
    drive_id INTEGER NOT NULL REFERENCES PlacementDrive(id) ON DELETE CASCADE,
               
    -- Resume snapshot (CRITICAL ADDITION)
    resume_snapshot_path VARCHAR NOT NULL,

    -- Student Answers (Application Form)
    related_work TEXT NOT NULL,
    related_projects TEXT NOT NULL,
    job_fit_statement TEXT NOT NULL,

    -- Status Tracking
    status VARCHAR NOT NULL DEFAULT 'Applied'
        CHECK (status IN (
            'Applied',
            'Shortlisted',
            'Interview',
            'Rejected',
            'Placed'
        )),

    -- Timestamps
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Notification tracking
    last_seen_status VARCHAR DEFAULT 'Applied',

    -- Prevent duplicate applications
    UNIQUE (student_id, drive_id)
);

-- ---------------- PLACEMENT TABLE ----------------
CREATE TABLE Placement (
    id SERIAL PRIMARY KEY,

    application_id INTEGER NOT NULL UNIQUE REFERENCES Application(id) ON DELETE CASCADE,
    offer_package VARCHAR,
    joining_date DATE,

    placement_status VARCHAR DEFAULT 'Confirmed'
        CHECK (placement_status IN ('Confirmed','Joined','Declined')),

    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------- RDBMS FEATURES ----------------

-- 1. TRIGGER: FOR AUTOMATIC TIMESTAMPS
-- This function updates the 'updated_at' column to the current time
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for each table that needs automatic timestamps
CREATE TRIGGER update_company_modtime BEFORE UPDATE ON Company FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_student_modtime BEFORE UPDATE ON Student FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_drive_modtime BEFORE UPDATE ON PlacementDrive FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- 2. STORED PROCEDURE (FUNCTION): BLACKLIST LOGIC
-- Automatically rejects all 'Applied' or 'Shortlisted' applications when a student is blacklisted
CREATE OR REPLACE FUNCTION blacklist_student_with_cleanup(s_id INTEGER)
RETURNS VOID AS $$
DECLARE
    -- CURSOR usage example: for iterating over pending applications
    app_cursor CURSOR FOR SELECT id FROM Application WHERE student_id = s_id AND status IN ('Applied', 'Shortlisted');
    app_record RECORD;
BEGIN
    -- Update student status
    UPDATE Student SET is_blacklisted = 1 WHERE id = s_id;

    -- Open cursor and iterate
    OPEN app_cursor;
    LOOP
        FETCH app_cursor INTO app_record;
        EXIT WHEN NOT FOUND;
        
        -- Reject the application
        UPDATE Application SET status = 'Rejected' WHERE id = app_record.id;
    END LOOP;
    CLOSE app_cursor;
END;
$$ LANGUAGE plpgsql;

-- 3. TRIGGER FOR APPLICATION UPDATES
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_application_modtime BEFORE UPDATE ON Application FOR EACH ROW EXECUTE PROCEDURE update_last_updated_column();
