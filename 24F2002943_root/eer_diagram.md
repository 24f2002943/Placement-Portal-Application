# Placement Portal EER Diagram

This diagram represents the Enhanced Entity-Relationship model for the Placement Portal Application.

```mermaid
erDiagram
    ADMIN ||--o{ COMPANY : "approves"
    COMPANY ||--o{ PLACEMENT_DRIVE : "posts"
    STUDENT ||--o{ APPLICATION : "submits"
    PLACEMENT_DRIVE ||--o{ APPLICATION : "receives"
    APPLICATION ||--o| PLACEMENT : "results in"

    ADMIN {
        integer id PK
        text username
        text password_hash
    }

    COMPANY {
        integer id PK
        text name
        text email
        text password_hash
        text phone
        text website
        text location
        text description
        text industry
        text approval_status "Pending, Approved, Rejected"
        integer is_blacklisted "0, 1"
        integer approved_by FK
        datetime approved_date
        datetime created_at
        datetime updated_at
    }

    STUDENT {
        integer id PK
        text full_name
        text email
        text password_hash
        text phone
        text degree
        text branch
        text college
        float cgpa
        text skills
        text resume_path
        integer is_blacklisted "0, 1"
        datetime created_at
        datetime updated_at
    }

    PLACEMENT_DRIVE {
        integer id PK
        integer company_id FK
        text title
        text description
        text location
        text required_skills
        text experience_required
        integer min_salary
        integer max_salary
        date deadline
        text approval_status "Pending, Approved, Rejected"
        text drive_status "Active, Closed"
        datetime created_at
        datetime updated_at
    }

    APPLICATION {
        integer id PK
        integer student_id FK
        integer drive_id FK
        text resume_snapshot_path
        text related_work
        text related_projects
        text job_fit_statement
        text status "Applied, Shortlisted, Interview, Rejected, Placed"
        datetime applied_at
        datetime last_updated
        text last_seen_status
    }

    PLACEMENT {
        integer id PK
        integer application_id FK
        text offer_package
        date joining_date
        text placement_status "Confirmed, Joined, Declined"
        datetime placed_at
    }
```

## Key Relationships
- **Admin → Company**: One administrator can approve/manage multiple company registrations.
- **Company → PlacementDrive**: Each company can post multiple job opportunities (drives).
- **Student → Application**: A student can apply to multiple placement drives.
- **PlacementDrive → Application**: A single drive can receive applications from multiple students.
- **Application → Placement**: If an application is successful (status 'Placed'), it generates a single placement record (1:1 relationship).

## Integrity Constraints
- **Foreign Keys**: All relationships are enforced via foreign keys with `ON DELETE CASCADE` or `SET NULL` as appropriate.
- **Status Checks**: Fields like `approval_status`, [drive_status](file:///c:/Users/Tanaya/Desktop/24f2002943/24F2002943_root/app.py#905-941), and [application_status](file:///c:/Users/Tanaya/Desktop/24f2002943/24F2002943_root/app.py#943-998) have explicit `CHECK` constraints to ensure data validity.
- **Uniqueness**: `student_id` and `drive_id` combination in the `Application` table is unique to prevent duplicate applications.
