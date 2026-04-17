# Normalized Database Schema (3NF)

The following schema represents the Placement Portal database in **Third Normal Form (3NF)**.

## 1. Admin Table
Stores administrative credentials for platform management.
- **id** (PK, Integer)
- **username** (Unique Text)
- **password_hash** (Text)

## 2. Company Table
Stores company profiles and approval status.
- **id** (PK, Integer)
- **name** (Text)
- **email** (Unique Text)
- **password_hash** (Text)
- **phone** (Text)
- **website** (Text)
- **location** (Text)
- **description** (Text)
- **industry** (Text)
- **approval_status** (Text: 'Pending', 'Approved', 'Rejected')
- **is_blacklisted** (Boolean: 0, 1)
- **approved_by** (FK -> Admin.id)
- **approved_date** (DateTime)
- **created_at** (DateTime)
- **updated_at** (DateTime)

## 3. Student Table
Stores student profiles and academic history.
- **id** (PK, Integer)
- **full_name** (Text)
- **email** (Unique Text)
- **password_hash** (Text)
- **phone** (Text)
- **degree** (Text)
- **branch** (Text)
- **college** (Text)
- **cgpa** (Real)
- **skills** (Text)
- **resume_path** (Text)
- **is_blacklisted** (Boolean: 0, 1)
- **created_at** (DateTime)
- **updated_at** (DateTime)

## 4. PlacementDrive Table
Stores job opportunities posted by Companies.
- **id** (PK, Integer)
- **company_id** (FK -> Company.id, CASCADE)
- **title** (Text)
- **description** (Text)
- **location** (Text)
- **required_skills** (Text)
- **experience_required** (Text)
- **min_salary** (Integer)
- **max_salary** (Integer)
- **deadline** (Date)
- **approval_status** (Text: 'Pending', 'Approved', 'Rejected')
- **drive_status** (Text: 'Active', 'Closed')
- **created_at** (DateTime)
- **updated_at** (DateTime)

## 5. Application Table
*Junction Table* resolving the Many-to-Many relationship between Students and Drives.
- **id** (PK, Integer)
- **student_id** (FK -> Student.id, CASCADE)
- **drive_id** (FK -> PlacementDrive.id, CASCADE)
- **resume_snapshot_path** (Text)
- **related_work** (Text)
- **related_projects** (Text)
- **job_fit_statement** (Text)
- **status** (Text: 'Applied', 'Shortlisted', 'Interview', 'Rejected', 'Placed')
- **applied_at** (DateTime)
- **last_updated** (DateTime)
- **last_seen_status** (Text)
- *Unique Constraint*: (student_id, drive_id)

## 6. Placement Table
Stores final records for students who are successfully placed.
- **id** (PK, Integer)
- **application_id** (FK -> Application.id, CASCADE, Unique)
- **offer_package** (Text)
- **joining_date** (Date)
- **placement_status** (Text: 'Confirmed', 'Joined', 'Declined')
- **placed_at** (DateTime)
