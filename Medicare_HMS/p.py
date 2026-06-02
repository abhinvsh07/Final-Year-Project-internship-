import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "database.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def user_exists(cur, username):
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    return cur.fetchone()


def create_demo_users():
    conn = get_connection()
    cur = conn.cursor()

    # ----------------------------
    # Departments
    # ----------------------------
    departments = [
        ("General Medicine", "General OPD", "doctor"),
        ("Cardiology", "Heart Department", "doctor"),
        ("Neurology", "Brain and Nerves", "doctor"),
        ("Reception", "Front Desk", "staff"),
        ("Accounts", "Billing and Finance", "staff"),
    ]

    dept_ids = {}

    for name, desc, dept_type in departments:
        cur.execute(
            "SELECT id FROM departments WHERE name = ?",
            (name,)
        )
        existing = cur.fetchone()

        if existing:
            dept_ids[name] = existing["id"]
        else:
            cur.execute("""
                INSERT INTO departments (name, description, department_type)
                VALUES (?, ?, ?)
            """, (name, desc, dept_type))

            dept_ids[name] = cur.lastrowid

    # ----------------------------
    # Patients
    # ----------------------------
    patients = [
        ("p1", "Rahul Sharma", "male", "O+"),
        ("p2", "Priya Singh", "female", "A+"),
        ("p3", "Amit Verma", "male", "B+"),
    ]

    for username, name, gender, blood_group in patients:

        if user_exists(cur, username):
            continue

        cur.execute("""
            INSERT INTO users
            (username, email, password_hash, name, role, gender, blood_group)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            username,
            f"{username}@medicare.com",
            generate_password_hash(username),
            name,
            "patient",
            gender,
            blood_group
        ))

        user_id = cur.lastrowid

        cur.execute("""
            INSERT INTO patients (user_id, emergency_contact)
            VALUES (?, ?)
        """, (
            user_id,
            "9999999999"
        ))

    # ----------------------------
    # Doctors
    # ----------------------------
    doctors = [
        (
            "d1",
            "Dr. Arjun Mehta",
            "male",
            "A+",
            "General Physician",
            "General Medicine",
            500,
            "LIC-D101",
            2500,
            5
        ),
        (
            "d2",
            "Dr. Neha Kapoor",
            "female",
            "AB+",
            "Cardiologist",
            "Cardiology",
            1200,
            "LIC-D102",
            5000,
            10
        ),
        (
            "d3",
            "Dr. Vikram Rao",
            "male",
            "B+",
            "Neurologist",
            "Neurology",
            1500,
            "LIC-D103",
            6500,
            12
        ),
    ]

    for (
        username,
        name,
        gender,
        blood_group,
        specialization,
        department,
        fee,
        license_no,
        salary,
        experience
    ) in doctors:

        if user_exists(cur, username):
            continue

        cur.execute("""
            INSERT INTO users
            (username, email, password_hash, name, role, gender, blood_group)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            username,
            f"{username}@medicare.com",
            generate_password_hash(username),
            name,
            "doctor",
            gender,
            blood_group
        ))

        user_id = cur.lastrowid

        cur.execute("""
            INSERT INTO doctors (
                user_id,
                specialization,
                department_id,
                consultation_fee,
                license_number,
                per_day_salary,
                experience_years
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            specialization,
            dept_ids[department],
            fee,
            license_no,
            salary,
            experience
        ))

    # ----------------------------
    # Staff
    # ----------------------------
    staff_members = [
        (
            "s1",
            "Riya Desk",
            "female",
            "O+",
            "Receptionist",
            "Reception",
            900,
            "day"
        ),
        (
            "s2",
            "Karan Finance",
            "male",
            "A-",
            "Accountant",
            "Accounts",
            1200,
            "day"
        ),
    ]

    for (
        username,
        name,
        gender,
        blood_group,
        designation,
        department,
        salary,
        shift
    ) in staff_members:

        if user_exists(cur, username):
            continue

        cur.execute("""
            INSERT INTO users
            (username, email, password_hash, name, role, gender, blood_group)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            username,
            f"{username}@medicare.com",
            generate_password_hash(username),
            name,
            "staff",
            gender,
            blood_group
        ))

        user_id = cur.lastrowid

        cur.execute("""
            INSERT INTO staff (
                user_id,
                designation,
                department_id,
                per_day_salary,
                shift_type
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            designation,
            dept_ids[department],
            salary,
            shift
        ))

    conn.commit()
    conn.close()

    print("Demo users created successfully.")
import random
import datetime


def create_demo_data():

    conn = get_connection()
    cur = conn.cursor()

    # -----------------------------
    # FETCH PATIENTS
    # -----------------------------
    cur.execute("""
        SELECT p.id, u.name
        FROM patients p
        JOIN users u ON u.id = p.user_id
    """)
    patients = cur.fetchall()

    # -----------------------------
    # FETCH DOCTORS
    # -----------------------------
    cur.execute("""
        SELECT d.id, d.user_id, d.consultation_fee
        FROM doctors d
    """)
    doctors = cur.fetchall()

    # -----------------------------
    # FETCH STAFF
    # -----------------------------
    cur.execute("""
        SELECT s.user_id, s.per_day_salary
        FROM staff s
    """)
    staff_members = cur.fetchall()

    today = datetime.date.today()

    # =====================================================
    # APPOINTMENTS + MEDICAL RECORDS + BILLS
    # =====================================================

    diagnoses = [
        "Viral Fever",
        "Migraine",
        "Hypertension",
        "Diabetes",
        "Chest Infection"
    ]

    prescriptions = [
        "Paracetamol twice daily",
        "Bed rest and hydration",
        "Blood pressure medication",
        "Antibiotics for 5 days",
        "Regular monitoring advised"
    ]

    for patient in patients:

        for i in range(3):

            doctor = random.choice(doctors)

            appointment_date = today - datetime.timedelta(days=random.randint(1, 30))

            appointment_time = datetime.datetime.combine(
                appointment_date,
                datetime.time(hour=random.randint(9, 17))
            )

            status = random.choice([
                "completed",
                "completed",
                "completed",
                "pending",
                "confirmed"
            ])

            cur.execute("""
                INSERT INTO appointments (
                    patient_id,
                    doctor_id,
                    consultation_fee,
                    appointment_time,
                    status,
                    reason
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                patient["id"],
                doctor["id"],
                doctor["consultation_fee"],
                appointment_time.strftime("%Y-%m-%d %H:%M:%S"),
                status,
                "General Checkup"
            ))

            appointment_id = cur.lastrowid

            # completed appointments
            if status == "completed":

                diagnosis = random.choice(diagnoses)
                prescription = random.choice(prescriptions)

                cur.execute("""
                    INSERT INTO medical_records (
                        patient_id,
                        doctor_id,
                        appointment_id,
                        diagnosis,
                        prescription_notes
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    patient["id"],
                    doctor["id"],
                    appointment_id,
                    diagnosis,
                    prescription
                ))

                bill_status = random.choice([
                    "paid",
                    "unpaid",
                    "partial"
                ])

                cur.execute("""
                    INSERT INTO bills (
                        patient_id,
                        doctor_id,
                        appointment_id,
                        total_amount,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    patient["id"],
                    doctor["id"],
                    appointment_id,
                    doctor["consultation_fee"],
                    bill_status
                ))

    # =====================================================
    # ATTENDANCE
    # =====================================================

    all_users = []

    cur.execute("""
        SELECT user_id, per_day_salary
        FROM doctors
    """)
    all_users.extend(cur.fetchall())

    all_users.extend(staff_members)

    current_month = today.month
    current_year = today.year

    for entry in all_users:

        user_id = entry["user_id"]

        for day in range(1, 21):

            date_obj = datetime.date(current_year, current_month, day)

            status = random.choice([
                "present",
                "present",
                "present",
                "half-day",
                "absent"
            ])

            try:

                cur.execute("""
                    INSERT INTO attendance (
                        user_id,
                        date,
                        status
                    )
                    VALUES (?, ?, ?)
                """, (
                    user_id,
                    date_obj.isoformat(),
                    status
                ))

            except:
                pass

    # =====================================================
    # SALARY SLIPS
    # =====================================================

    # doctors
    cur.execute("""
        SELECT d.user_id,
               d.per_day_salary,
               d.id
        FROM doctors d
    """)

    doctors_full = cur.fetchall()

    for doc in doctors_full:

        user_id = doc["user_id"]

        cur.execute("""
            SELECT COUNT(*)
            FROM attendance
            WHERE user_id=?
            AND status='present'
            AND substr(date,1,7)=?
        """, (
            user_id,
            f"{current_year:04d}-{current_month:02d}"
        ))

        present_days = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM appointments
            WHERE doctor_id=?
            AND status='completed'
            AND substr(appointment_time,1,7)=?
        """, (
            doc["id"],
            f"{current_year:04d}-{current_month:02d}"
        ))

        completed = cur.fetchone()[0]

        appointment_earnings = completed * 500

        net_salary = (
            present_days * doc["per_day_salary"]
            +
            appointment_earnings
        )

        cur.execute("""
            INSERT OR IGNORE INTO salary_slips (
                user_id,
                month,
                year,
                per_day_salary,
                appointment_earnings,
                present_days,
                absent_days,
                bonus,
                deductions,
                net_salary,
                total_paid,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            current_month,
            current_year,
            doc["per_day_salary"],
            appointment_earnings,
            present_days,
            30 - present_days,
            1000,
            500,
            net_salary,
            1,
            "paid"
        ))

    # staff salary
    for staff in staff_members:

        user_id = staff["user_id"]

        cur.execute("""
            SELECT COUNT(*)
            FROM attendance
            WHERE user_id=?
            AND status='present'
            AND substr(date,1,7)=?
        """, (
            user_id,
            f"{current_year:04d}-{current_month:02d}"
        ))

        present_days = cur.fetchone()[0]

        net_salary = (
            present_days *
            staff["per_day_salary"]
        )

        cur.execute("""
            INSERT OR IGNORE INTO salary_slips (
                user_id,
                month,
                year,
                per_day_salary,
                present_days,
                absent_days,
                bonus,
                deductions,
                net_salary,
                total_paid,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            current_month,
            current_year,
            staff["per_day_salary"],
            present_days,
            30 - present_days,
            500,
            200,
            net_salary,
            1,
            "paid"
        ))

    # =====================================================
    # LEAVES
    # =====================================================

    for staff in staff_members:

        cur.execute("""
            INSERT INTO leaves (
                user_id,
                from_date,
                to_date,
                reason,
                status
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            staff["user_id"],
            (today + datetime.timedelta(days=5)).isoformat(),
            (today + datetime.timedelta(days=7)).isoformat(),
            "Personal leave",
            random.choice([
                "approved",
                "pending"
            ])
        ))

    conn.commit()
    conn.close()

    print("Demo relational data created successfully.")



if __name__ == "__main__":
    
    create_demo_data()