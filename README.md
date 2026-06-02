````markdown
# Medicare HMS (Hospital Management System)

Medicare HMS is a web-based Hospital Management System built with **Flask**, **SQLite**, **HTML/CSS**, and **JavaScript**. It provides a centralized platform for managing hospital operations including patient records, appointments, billing, attendance, staff management, and role-based dashboards.

---

## Features

### Authentication & Authorization
- Secure login system
- Patient self-registration
- Password hashing using Werkzeug
- Role-based access control
  - Admin
  - Doctor
  - Patient
  - Staff

### Admin Panel
- Create and manage users
- Manage doctors, patients, and staff
- Department management
- Attendance monitoring
- Hospital statistics dashboard
- View pending appointments
- Track unpaid bills

### Doctor Module
- Doctor dashboard
- View assigned patients
- Access patient medical history
- Manage appointments
- Maintain medical records
- Profile management

### Patient Module
- Patient registration
- Patient dashboard
- Book appointments
- View appointment history
- Access medical records
- View billing information
- Profile management

### Staff Module
- Staff dashboard
- Attendance tracking
- Salary calculation
- Leave management
- Profile management

### Billing System
- Generate bills
- Track payment status
- View unpaid bills
- Billing management dashboard

### Attendance Management
- Automatic attendance marking on login
- Attendance records for staff
- Attendance tracking dashboard

---

## Technology Stack

| Technology |        Usage             |
|------------|--------------------------|
| Flask      | Backend Framework        |
| SQLite     | Database                 |
| HTML5      | Frontend Structure       |
| CSS3       | Styling                  |
| JavaScript | Client-side Functionality|
| Werkzeug   | Password Security        |

---

## Project Structure

```text
Medicare_HMS/
│
├── app.py
├── db.py
├── db_init.py
├── database.db
│
├── static/
│   ├── css/
│   └── js/
│
├── templates/
│   ├── admin/
│   ├── appointments/
│   ├── attendance/
│   ├── auth/
│   ├── billing/
│   ├── dashboards/
│   ├── manage/
│   ├── medical_records/
│   ├── profile/
│   └── salary/
│
└── demo_accounts.txt
````

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/Medicare_HMS.git
cd Medicare_HMS
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install flask werkzeug
```

### 5. Initialize Database

```bash
python db_init.py
```

### 6. Run Application

```bash
python app.py
```

### 7. Open Browser

```text
http://127.0.0.1:5000
```

---

## Demo Accounts

### Admin

| Username | Password |
| -------- | -------- |
| admin    | admin123 |

### Doctors

| Username | Password |
| -------- | -------- |
| d1       | d1       |
| d2       | d2       |
| d3       | d3       |

### Patients

| Username | Password |
| -------- | -------- |
| p1       | p1       |
| p2       | p2       |
| p3       | p3       |

### Staff

| Username | Password |
| -------- | -------- |
| s1       | s1       |
| s2       | s2       |

---

## Database Modules

The system manages:

* Users
* Patients
* Doctors
* Staff
* Departments
* Appointments
* Medical Records
* Attendance
* Leaves
* Bills

---

## Security Features

* Password hashing
* Session-based authentication
* Role-based access restrictions
* Input validation
* Protected dashboards

---

## Screens Included

* Login Page
* Registration Page
* Admin Dashboard
* Doctor Dashboard
* Patient Dashboard
* Staff Dashboard
* Appointment Management
* Medical Records
* Billing System
* Attendance Tracking

---

## Future Improvements

* Email notifications
* Prescription generation
* Laboratory management
* Pharmacy integration
* Online payment gateway
* Report exports (PDF/Excel)
* SMS appointment reminders
* REST API support

---

## License

This project is intended for educational and academic purposes.

---

## Author

**Abhinav Sharma**

Hospital Management System developed using Flask and SQLite to simplify hospital administration, patient management, appointment scheduling, billing, and staff operations.

```

This README is formatted for direct use as a GitHub `README.md` file.
```
