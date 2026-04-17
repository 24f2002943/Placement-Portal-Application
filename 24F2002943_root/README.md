# 🎓 Placement Portal Application

## 📌 Project Overview
The Placement Portal Application is a web-based system designed to manage the campus recruitment process.  
It connects **students**, **companies**, and **administrators** on a centralized platform.

Students can apply to placement drives, companies can manage applicants, and administrators can control approvals and system activities.

---

## 🚀 Key Features

- **🎓 Student Dashboard:**  
  View placement drives, upload resumes, apply for jobs, and track application status.

- **🏢 Company Dashboard:**  
  Post placement drives, view applicants, and update application status.

- **🛠 Admin Dashboard:**  
  Approve companies, manage drives, and monitor platform activity.

- **📄 Resume Management:**  
  Students upload resumes and a snapshot of the resume is stored during job applications.

- **📊 Data Visualization:**  
  Charts and statistics for system insights using Chart.js.

- **🔐 Authentication & Role Management:**  
  Secure login system for Admin, Company, and Student roles.

---

## 🧰 Technologies Used

- **Flask** – Backend web framework  
- **Supabase (PostgreSQL)** – Cloud database engine  
- **Jinja2** – Template rendering engine  
- **Bootstrap 5** – Responsive frontend UI  
- **Chart.js** – Data visualization charts  
- **Flask-Login** – Authentication and session management  

---

## 💎 Advanced RDBMS Features
To demonstrate professional database management, this project implements:
- **Tiggers**: Automatic `updated_at` timestamps for data integrity.
- **Stored Procedures (Functions)**: Atomic blacklisting logic executed on the server.
- **Database Cursors**: Row-by-row processing within stored functions for complex cleanups.

---

## 📌 Milestones

### 1️⃣ Database Design
- Designed relational schema for placement portal.
- Created tables for Admin, Company, Student, PlacementDrive, Application, and Placement.

### 2️⃣ Authentication System
- Implemented login and registration.
- Role-based access for Admin, Company, and Student.

### 3️⃣ Placement Drive Management
- Companies can post placement drives.
- Admin approves drives before they go live.

### 4️⃣ Student Job Applications
- Students can apply for placement drives.
- Resume snapshot stored at time of application.

### 5️⃣ Application Tracking
- Companies update application status.
- Students track application progress.

---

## 🗄 Database Tables

- **Admin** – Stores administrator credentials  
- **Company** – Company profiles and approval status  
- **Student** – Student details and resume information  
- **PlacementDrive** – Job opportunities posted by companies  
- **Application** – Student applications to placement drives  
- **Placement** – Final placement records  

---

## 📁 Project Structure

Placement-Portal/
│
├── app.py                  # Main Flask backend (Supabase SDK)
├── supabase_schema.sql     # Cloud database schema & RDBMS features
├── migrate_to_supabase.py  # Data migration script
├── .env                    # Cloud credentials (excluded from Git)
├── README.md               # Project documentation
│
├── static/
│   ├── images/
│   └── uploads/            # Local resume storage
│
├── templates/              # HTML templates
│   ├── admin/
│   ├── company/
│   └── student/
│
└── requirements.txt        # Python dependencies

---

## 🗂 Database ER Diagram

The following ER diagram shows the relationships between the main database tables (Admin, Company, Student, PlacementDrive, Application, Placement).

<p align="center">
  <img src="Placement-Portal-Application/static/images/er_diagram.png" alt="ER Diagram" width="900">
</p>


<p align="center">
  <img src="./er_diagram.png" width="900">
</p>

## ⚙️ Setup & Installation
1.  **Clone the Repository**
2.  **Install dependencies**: `pip install -r requirements.txt`
3.  **Set up Supabase**:
    *   Create a new project on [Supabase](https://supabase.com/).
    *   Run the code in `supabase_schema.sql` in the Supabase SQL Editor.
4.  **Configure `.env`**: Add your `SUPABASE_URL` and `SUPABASE_KEY`.
5.  **Run the App**: `python app.py`

---
