from flask import Flask, render_template, redirect, session, request, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import re
import datetime
app = Flask(__name__)
app.secret_key = "your_secret_key"


ROLE_DASHBOARD = {
    "patient": "/dashboard/patient",
    "doctor": "/dashboard/doctor",
    "admin": "/dashboard/admin",
    "staff": "/dashboard/staff"
}


def get_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(ROLE_DASHBOARD.get(session.get('role'), '/login'))
    return render_template('auth/login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        uname = request.form.get('username')
        pw = request.form.get('password')

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username = ?", (uname,))
        user = cur.fetchone()

        if not user:
            conn.close()
            flash('User not found')
            return redirect('/')

        if not check_password_hash(user['password_hash'], pw):
            conn.close()
            flash('Invalid password')
            return redirect('/')

        # -------------------------
        # SESSION SET
        # -------------------------
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']

        user_id = user['id']   # FIX: define it properly

        # -------------------------
        # ATTENDANCE MARK
        # -------------------------
        today = datetime.date.today().isoformat()

        cur.execute("""
            SELECT id FROM attendance
            WHERE user_id=? AND date=?
        """, (user_id, today))

        exists = cur.fetchone()

        if not exists:
            cur.execute("""
                INSERT INTO attendance (user_id, date, status)
                VALUES (?, ?, 'present')
            """, (user_id, today))

        conn.commit()
        conn.close()

        return redirect(ROLE_DASHBOARD.get(user['role'], '/'))

    return render_template('auth/login.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        uname = request.form.get('username')
        pw = request.form.get('password')
        role = 'patient'

        pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$"

        if not re.match(pattern, pw):
            flash("Password is too weak")
            return render_template("auth/register.html")

        hashed_pw = generate_password_hash(pw)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users (username, email, password_hash, name, role)
            VALUES (?, ?, ?, ?, ?)
        """, (uname, email, hashed_pw, name, role))

        user_id = cur.lastrowid

        cur.execute("""
            INSERT INTO patients (user_id)
            VALUES (?)
        """, (user_id,))

        conn.commit()
        conn.close()

        flash("Account created successfully")
        return redirect('/login')

    return render_template('auth/register.html')

@app.route('/dashboard/admin')
def admin_dashboard():

    if session.get('role') != 'admin' or 'user_id' not in session:
        return redirect('/')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM doctors")
    total_doctors = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM patients")
    total_patients = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM staff")
    total_staff = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM departments")
    total_departments = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM appointments WHERE status='pending'")
    pending_appointments = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bills WHERE status='unpaid'")
    unpaid_bills = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-2 days')")
    recent_users = cur.fetchone()[0]

    conn.close()

    return render_template(
        'dashboards/admin.html',
        total_users=total_users,
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_staff=total_staff,
        total_departments=total_departments,
        pending_appointments=pending_appointments,
        unpaid_bills=unpaid_bills,
        recent_users=recent_users
        )

@app.route('/dashboard/doctor')
def doctor_dashboard():

    if session.get('role') != 'doctor':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM doctors WHERE user_id=?", (user_id,))
    doc = cur.fetchone()

    if not doc:
        conn.close()
        return redirect('/')

    doctor_id = doc['id']

    cur.execute("""
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed,
            COUNT(DISTINCT patient_id) AS patients
        FROM appointments
        WHERE doctor_id=?
    """, (doctor_id,))

    stats = cur.fetchone()

    today = datetime.date.today().isoformat()

    cur.execute("""
        SELECT 
            a.appointment_time,
            a.reason,
            a.status,
            u.name AS patient_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN users u ON u.id = p.user_id
        WHERE a.doctor_id=?
        AND substr(a.appointment_time,1,10)=?
        ORDER BY a.appointment_time
    """, (doctor_id, today))

    today_appointments = cur.fetchall()

    conn.close()

    return render_template(
        "dashboards/doctor.html",
        total_appointments=stats['total'],
        pending_appointments=stats['pending'],
        completed_appointments=stats['completed'],
        total_patients=stats['patients'],
        today_appointments=today_appointments
    )
@app.route('/dashboard/staff')
def staff_dashboard():

    if session.get('role') != 'staff':
        return redirect('/')

    user_id = session.get('user_id')

    today = datetime.date.today()
    month_key_value = f"{today.year:04d}-{today.month:02d}"

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE user_id=?
        AND status='present'
        AND substr(date,1,7)=?
    """, (user_id, month_key_value))

    present_days = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE user_id=?
        AND substr(date,1,7)=?
    """, (user_id, month_key_value))

    total_days = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM leaves
        WHERE user_id=?
        AND status='approved'
    """, (user_id,))

    leaves_count = cur.fetchone()[0]

    cur.execute("""
        SELECT per_day_salary
        FROM staff
        WHERE user_id=?
    """, (user_id,))

    row = cur.fetchone()
    per_day_salary = row[0] if row else 0

    salary = per_day_salary * present_days

    conn.close()

    return render_template(
        "dashboards/staff.html",
        present_days=present_days,
        total_days=total_days,
        leaves_count=leaves_count,
        salary=salary
    )



@app.route('/dashboard/patient')
def patient_dashboard():

    user_id = session.get('user_id')
    role = session.get('role')

    if not user_id or role != 'patient':
        return redirect('/')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM patients WHERE user_id=?", (user_id,))
    patient = cur.fetchone()

    if not patient:
        conn.close()
        return "Patient profile not found", 404

    pid = patient["id"]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE patient_id=?", (pid,))
    total_appointments = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM appointments
        WHERE patient_id=? AND status='pending'
    """, (pid,))
    pending_appointments = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM appointments
        WHERE patient_id=? AND status='completed'
    """, (pid,))
    completed_appointments = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM bills
        WHERE patient_id=? AND status='unpaid'
    """, (pid,))
    unpaid_bills = cur.fetchone()[0]

    conn.close()

    return render_template(
        "dashboards/patient.html",
        total_appointments=total_appointments,
        pending_appointments=pending_appointments,
        completed_appointments=completed_appointments,
        unpaid_bills=unpaid_bills
    )
@app.route('/admin/create-user', methods=['GET', 'POST'])
def create_user():

    if session.get('role') != 'admin':
        return redirect('/')

    conn = get_connection()
    cur = conn.cursor()

    try:

        if request.method == 'POST':

            name = request.form.get('name')
            email = request.form.get('email')
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role')

            extra = (
                request.form.get('specialization')
                or
                request.form.get('designation')
            )

            dept = request.form.get('department_id')

            pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$"

            if not re.match(pattern, password):

                flash("Password is too weak")

                cur.execute("SELECT * FROM departments")
                departments = cur.fetchall()

                return render_template(
                    "admin/create_user.html",
                    departments=departments
                )

            cur.execute("""
                SELECT id
                FROM users
                WHERE username=?
            """, (username,))

            existing_user = cur.fetchone()

            if existing_user:

                flash("Username already exists")

                cur.execute("SELECT * FROM departments")
                departments = cur.fetchall()

                return render_template(
                    "admin/create_user.html",
                    departments=departments
                )

            hashed_pw = generate_password_hash(password)

            cur.execute("""
                INSERT INTO users (
                    username,
                    email,
                    password_hash,
                    name,
                    role
                )
                VALUES (?, ?, ?, ?, ?)
            """, (

                username,
                email,
                hashed_pw,
                name,
                role

            ))

            user_id = cur.lastrowid

            if role == "doctor":

                cur.execute("""
                    INSERT INTO doctors (
                        user_id,
                        specialization,
                        department_id
                    )
                    VALUES (?, ?, ?)
                """, (

                    user_id,
                    extra,
                    dept

                ))

            elif role == "staff":

                cur.execute("""
                    INSERT INTO staff (
                        user_id,
                        designation,
                        department_id
                    )
                    VALUES (?, ?, ?)
                """, (

                    user_id,
                    extra,
                    dept

                ))

            conn.commit()

            flash("User created successfully")

            return redirect("/admin/create-user")

        cur.execute("SELECT * FROM departments")
        departments = cur.fetchall()

        return render_template(
            "admin/create_user.html",
            departments=departments
        )

    except Exception as e:

        conn.rollback()

        raise e

    finally:

        conn.close()

# @app.route("/admin/manage/departments", methods=["GET", "POST"])
# def manage_departments():

#     if session.get("role") != "admin":
#         return redirect("/")

#     conn = get_connection()
#     cur = conn.cursor()

#     edit_dept = None

#     if request.method == "POST":

#         dept_id = request.form.get("dept_id")
#         name = request.form["name"].strip()
#         description = request.form["description"].strip()

#         if dept_id:

#             cur.execute("""
#                 SELECT id FROM departments
#                 WHERE name = ? AND id != ?
#             """, (name, dept_id))

#             if cur.fetchone():
#                 flash("Department name already exists", "error")
#             else:
#                 cur.execute("""
#                     UPDATE departments
#                     SET name = ?, description = ?
#                     WHERE id = ?
#                 """, (name, description, dept_id))
#                 conn.commit()

#         else:

#             cur.execute("SELECT id FROM departments WHERE name = ?", (name,))

#             if cur.fetchone():
#                 flash("Department already exists", "error")
#             else:
#                 cur.execute("""
#                     INSERT INTO departments (name, description)
#                     VALUES (?, ?)
#                 """, (name, description))
#                 conn.commit()

#     edit_id = request.args.get("edit_id")

#     if edit_id:
#         cur.execute("SELECT * FROM departments WHERE id = ?", (edit_id,))
#         edit_dept = cur.fetchone()

#     delete_id = request.args.get("delete_id")

#     if delete_id:

#         cur.execute("SELECT COUNT(*) FROM doctors WHERE department_id = ?", (delete_id,))
#         doctor_count = cur.fetchone()[0]

#         cur.execute("SELECT COUNT(*) FROM staff WHERE department_id = ?", (delete_id,))
#         staff_count = cur.fetchone()[0]

#         if doctor_count == 0 and staff_count == 0:
#             cur.execute("DELETE FROM departments WHERE id = ?", (delete_id,))
#             conn.commit()
#         else:
#             flash("Cannot delete: department is assigned to doctors or staff", "error")

#     cur.execute("""
#         SELECT 
#             d.id,
#             d.name,
#             d.description,
#             (SELECT COUNT(*) FROM doctors WHERE department_id = d.id) AS doctor_count,
#             (SELECT COUNT(*) FROM staff WHERE department_id = d.id) AS staff_count
#         FROM departments d
#         ORDER BY d.name
#     """)

#     departments = cur.fetchall()

#     conn.close()

#     return render_template(
#         "/manage/departments.html",
#         departments=departments,
#         edit_dept=edit_dept
#     )


# @app.route("/admin/manage/doctors")
# def manage_doctors():

#     if session.get("role") != "admin":
#         return redirect("/")

#     conn = get_connection()
#     cur = conn.cursor()

#     delete_id = request.args.get("delete_id")
#     edit_id = request.args.get("edit_id")

#     if delete_id:

#         cur.execute("SELECT user_id FROM doctors WHERE id = ?", (delete_id,))
#         row = cur.fetchone()

#         if row:

#             cur.execute("DELETE FROM doctors WHERE id = ?", (delete_id,))
#             cur.execute("DELETE FROM users WHERE id = ?", (row["user_id"],))

#             conn.commit()

#     doctor_edit = None

#     if edit_id:

#         cur.execute("""
#             SELECT d.*, u.name, u.email, u.username
#             FROM doctors d
#             JOIN users u ON u.id = d.user_id
#             WHERE d.id = ?
#         """, (edit_id,))

#         doctor_edit = cur.fetchone()

#     cur.execute("""
#         SELECT 
#             d.id,
#             u.name,
#             u.email,
#             u.username,
#             d.specialization,
#             d.department_id,
#             dept.name AS department_name
#         FROM doctors d
#         JOIN users u ON u.id = d.user_id
#         LEFT JOIN departments dept ON dept.id = d.department_id
#         ORDER BY u.name
#     """)

#     doctors = cur.fetchall()

#     conn.close()

#     return render_template("/manage/mdoctor.html", doctors=doctors, doctor_edit=doctor_edit)


# @app.route('/admin/manage/patients')
# def manage_patients():

#     if session.get('role') != 'admin':
#         return redirect('/')

#     conn = get_connection()
#     cur = conn.cursor()

#     delete_id = request.args.get('delete_id')

#     if delete_id:
#         cur.execute("DELETE FROM users WHERE id=?", (delete_id,))
#         conn.commit()
#         conn.close()
#         return redirect('/admin/manage/patients')

#     cur.execute("""
#         SELECT 
#             u.id,
#             u.name,
#             u.username,
#             u.email,
#             p.gender,
#             p.blood_group
#         FROM users u
#         LEFT JOIN patients p ON p.user_id = u.id
#         WHERE u.role = 'patient'
#     """)

#     patients = cur.fetchall()
#     conn.close()

#     return render_template("manage/mpatients.html", patients=patients)

# @app.route('/admin/manage/staff')
# def manage_staff():

#     if session.get('role') != 'admin':
#         return redirect('/')

#     conn = get_connection()
#     cur = conn.cursor()

#     cur.execute("""
#         SELECT s.id, u.name, u.username, u.email,
#                s.designation,
#                dep.name AS department_name
#         FROM staff s
#         JOIN users u ON u.id = s.user_id
#         LEFT JOIN departments dep ON dep.id = s.department_id
#     """)

#     staff = cur.fetchall()
#     conn.close()

#     return render_template("/manage/mstaff.html", staff=staff)




@app.route('/admin/manage/<entity>', methods=['GET', 'POST'])
def manage(entity):
    if session.get('role') != 'admin':
        return redirect('/')

    conn = get_connection()
    cur = conn.cursor()

    # departments for dropdown
    cur.execute("SELECT * FROM departments ORDER BY name")
    departments = cur.fetchall()

    doctor_departments = [d for d in departments if d["department_type"] == "doctor"]
    staff_departments = [d for d in departments if d["department_type"] == "staff"]

    delete_id = request.args.get("delete_id")

    if delete_id:
        if entity == "departments":
            cur.execute("DELETE FROM departments WHERE id=?", (delete_id,))
        else:
            cur.execute("DELETE FROM users WHERE id=?", (delete_id,))
        conn.commit()
        return redirect(f"/admin/manage/{entity}")

    # ================= PATIENTS =================
    if entity == "patients":
        if request.method == "POST":
            uid = request.form["id"]
            username = request.form["username"]

            cur.execute("SELECT id FROM users WHERE username=? AND id!=?", (username, uid))
            if cur.fetchone():
                flash("Username already exists", "error")
                return redirect(f"/admin/manage/{entity}")

            cur.execute("""
                UPDATE users
                SET name=?, username=?, email=?, gender=?, blood_group=?, phone=?, address=?
                WHERE id=?
            """, (
                request.form["name"],
                username,
                request.form["email"],
                request.form.get("gender"),
                request.form.get("blood_group"),
                request.form.get("phone"),
                request.form.get("address"),
                uid
            ))

            cur.execute("""
                UPDATE patients
                SET emergency_contact=?
                WHERE user_id=?
            """, (request.form.get("emergency_contact"), uid))

            conn.commit()
            return redirect(f"/admin/manage/{entity}")

        cur.execute("""
            SELECT u.*, p.emergency_contact
            FROM users u
            JOIN patients p ON p.user_id = u.id
            WHERE u.role='patient'
        """)
        data = cur.fetchall()

    # ================= DOCTORS =================
    elif entity == "doctors":
        if request.method == "POST":
            uid = request.form["id"]
            username = request.form["username"]

            cur.execute("SELECT id FROM users WHERE username=? AND id!=?", (username, uid))
            if cur.fetchone():
                flash("Username already exists", "error")
                return redirect(f"/admin/manage/{entity}")

            cur.execute("""
                UPDATE users
                SET name=?, username=?, email=?, phone=?, address=?
                WHERE id=?
            """, (
                request.form["name"],
                username,
                request.form["email"],
                request.form.get("phone"),
                request.form.get("address"),
                uid
            ))

            cur.execute("""
    UPDATE doctors
    SET specialization=?, department_id=?, per_day_salary=?
    WHERE user_id=?
""", (
    request.form.get("specialization"),
    request.form.get("department_id") or None,
    request.form.get("salary"),
    uid
))

            conn.commit()
            return redirect(f"/admin/manage/{entity}")

        cur.execute("""
            SELECT u.*, d.specialization,per_day_salary,
                   dep.name AS department_name
            FROM users u
            JOIN doctors d ON d.user_id = u.id
            LEFT JOIN departments dep ON dep.id = d.department_id
            WHERE u.role='doctor'
        """)
        data = cur.fetchall()

    # ================= STAFF =================
    elif entity == "staff":
        if request.method == "POST":
            uid = request.form["id"]
            username = request.form["username"]

            cur.execute("SELECT id FROM users WHERE username=? AND id!=?", (username, uid))
            if cur.fetchone():
                flash("Username already exists", "error")
                return redirect(f"/admin/manage/{entity}")

            cur.execute("""
                UPDATE users
                SET name=?, username=?, email=?, phone=?, address=?
                WHERE id=?
            """, (
                request.form["name"],
                username,
                request.form["email"],
                request.form.get("phone"),
                request.form.get("address"),
                uid
            ))

            cur.execute("""
    UPDATE staff
    SET designation=?, department_id=?, per_day_salary=?
    WHERE user_id=?
""", (
    request.form.get("designation"),
    request.form.get("department_id") or None,
    request.form.get("salary"),
    uid
))
            cur.execute("""
                UPDATE staff
                SET designation=?, department_id=?
                WHERE user_id=?
            """, (
                request.form.get("designation"),
                request.form.get("department_id") or None,
                uid
            ))

            conn.commit()
            return redirect(f"/admin/manage/{entity}")

        cur.execute("""
            SELECT u.*, s.designation,per_day_salary,
                   dep.name AS department_name
            FROM users u
            JOIN staff s ON s.user_id = u.id
            LEFT JOIN departments dep ON dep.id = s.department_id
            WHERE u.role='staff'
        """)
        data = cur.fetchall()

    # ================= DEPARTMENTS =================
    elif entity == "departments":
        if request.method == "POST":
            dept_id = request.form.get("id")

            if dept_id:
                cur.execute("""
                    UPDATE departments
                    SET name=?, description=?, department_type=?
                    WHERE id=?
                """, (
                    request.form["name"],
                    request.form.get("description"),
                    request.form["department_type"],
                    dept_id
                ))
            else:
                cur.execute("""
                    INSERT INTO departments (name, description, department_type)
                    VALUES (?, ?, ?)
                """, (
                    request.form["name"],
                    request.form.get("description"),
                    request.form["department_type"]
                ))

            conn.commit()
            return redirect(f"/admin/manage/{entity}")

        cur.execute("SELECT * FROM departments")
        data = cur.fetchall()

    else:
        return redirect("/dashboard/admin")

    conn.close()

    return render_template(
        "manage/manage_entities.html",
        entity=entity,
        data=data,
        departments=departments,
        doctor_departments=doctor_departments,
        staff_departments=staff_departments
    )
@app.route('/admin/update', methods=['POST'])
def update_user():

    if session.get('role') != 'admin':
        return redirect('/')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET name = ?, email = ?
        WHERE id = ?
    """, (
        request.form.get('name'),
        request.form.get('email'),
        request.form.get('id')
    ))

    conn.commit()
    conn.close()

    return redirect(request.referrer)


# @app.route('/admin/manage/<entity>/edit', methods=['POST'])
# def edit_entity(entity):

#     if session.get('role') != 'admin':
#         return redirect('/')

#     conn = get_connection()
#     cur = conn.cursor()

#     if entity == "departments":

#         cur.execute("""
#             UPDATE departments
#             SET name=?, description=?
#             WHERE id=?
#         """, (
#             request.form.get('name'),
#             request.form.get('description'),
#             request.form.get('id')
#         ))

#     elif entity == "doctors":

#         cur.execute("""
#             UPDATE doctors
#             SET specialization=?, department_id=?,per_day_salary=?
#             WHERE id=?
#         """, (
#             request.form.get('specialization'),
#             request.form.get('department_id'),
#             request.form.get('salary'),
#             request.form.get('id')
#         ))
        

#         cur.execute("""
#             UPDATE users
#             SET name=?, email=?
#             WHERE id=(
#                 SELECT user_id FROM doctors WHERE id=?
#             )
#         """, (
#             request.form.get('name'),
#             request.form.get('email'),
#             request.form.get('id')
#         ))

#     elif entity == "staff":

#         cur.execute("""
#             UPDATE staff
#             SET designation=?, department_id=?
#             WHERE id=?
#         """, (
#             request.form.get('designation'),
#             request.form.get('department_id'),
#             request.form.get('id')
#         ))

#         cur.execute("""
#             UPDATE users
#             SET name=?, email=?
#             WHERE id=(
#                 SELECT user_id FROM staff WHERE id=?
#             )
#         """, (
#             request.form.get('name'),
#             request.form.get('email'),
#             request.form.get('id')
#         ))

#     elif entity == "patients":

#         cur.execute("""
#             UPDATE patients
#             SET gender=?, blood_group=?
#             WHERE id=?
#         """, (
#             request.form.get('gender'),
#             request.form.get('blood_group'),
#             request.form.get('id')
#         ))

#         cur.execute("""
#             UPDATE users
#             SET name=?, email=?
#             WHERE id=(
#                 SELECT user_id FROM patients WHERE id=?
#             )
#         """, (
#             request.form.get('name'),
#             request.form.get('email'),
#             request.form.get('id')
#         ))

#     conn.commit()
#     conn.close()

#     return redirect(f"/admin/manage/{entity}")

# APPOINTMENTS
@app.route('/patient/appointments')
def patient_appointments():

    if session.get('role') != 'patient':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM patients WHERE user_id=?", (user_id,))
    patient = cur.fetchone()

    if not patient:
        conn.close()
        return redirect('/')

    cur.execute("""
        SELECT d.id, u.name, d.specialization, d.consultation_fee
        FROM doctors d
        JOIN users u ON u.id = d.user_id
    """)
    doctors = cur.fetchall()

    cur.execute("""
        SELECT 
            a.id,
            a.appointment_time,
            a.reason,
            a.status,
            a.consultation_fee,
            u.name AS doctor_name,
            d.specialization
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        JOIN users u ON u.id = d.user_id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_time DESC
    """, (patient['id'],))

    rows = cur.fetchall()

    active = []
    history = []

    for r in rows:
        if r['status'] in ['pending', 'confirmed']:
            active.append(r)
        else:
            history.append(r)

    conn.close()

    return render_template(
        "appointments/apatient.html",
        doctors=doctors,
        active=active,
        history=history
    )


@app.route('/patient/book-appointment', methods=['POST'])
def book_appointment():

    if session.get('role') != 'patient':
        return redirect('/')

    user_id = session.get('user_id')

    doctor_id = request.form.get('doctor_id')
    time = request.form.get('appointment_time')
    reason = request.form.get('reason')

    import datetime

    conn = get_connection()
    cur = conn.cursor()

    # patient id
    cur.execute("SELECT id FROM patients WHERE user_id=?", (user_id,))
    patient = cur.fetchone()

    if not patient:
        conn.close()
        return redirect('/patient/appointments')

    # -------------------------
    # BASIC VALIDATION ONLY
    # -------------------------
    try:
        dt = datetime.datetime.fromisoformat(time)
    except:
        flash("Invalid date format", "danger")
        return redirect('/patient/appointments')

    today = datetime.date.today()
    selected_date = dt.date()

    # must be tomorrow or later
    if selected_date <= today:
        flash("You can only book from tomorrow onwards", "danger")
        return redirect('/patient/appointments')

    # time restriction 8 AM - 8 PM
    if dt.hour < 8 or dt.hour >= 20:
        flash("Appointments allowed only between 8 AM and 8 PM", "danger")
        return redirect('/patient/appointments')

    # get fee
    cur.execute("SELECT consultation_fee FROM doctors WHERE id=?", (doctor_id,))
    doc = cur.fetchone()
    fee = doc['consultation_fee'] if doc else 0

    # insert (store as standard format)
    cur.execute("""
        INSERT INTO appointments
        (patient_id, doctor_id, appointment_time, reason, status, consultation_fee)
        VALUES (?, ?, ?, ?, 'pending', ?)
    """, (
        patient['id'],
        doctor_id,
        dt.strftime("%Y-%m-%d %H:%M:%S"),
        reason,
        fee
    ))

    conn.commit()
    conn.close()

    flash("Appointment requested successfully", "success")

    return redirect('/patient/appointments')


@app.route('/doctor/appointments')
def doctor_appointments():

    if session.get('role') != 'doctor':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM doctors WHERE user_id=?", (user_id,))
    doctor = cur.fetchone()

    if not doctor:
        conn.close()
        return redirect('/')

    doctor_id = doctor['id']

    cur.execute("""
        SELECT 
            a.id,
            a.appointment_time,
            a.reason,
            a.status,
            u.name AS patient_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN users u ON u.id = p.user_id
        WHERE a.doctor_id = ?
        ORDER BY a.appointment_time DESC
    """, (doctor_id,))

    rows = cur.fetchall()
    conn.close()

    pending = []
    active = []
    history = []

    for a in rows:
        if a['status'] == 'pending':
            pending.append(a)
        elif a['status'] == 'confirmed':
            active.append(a)
        else:
            history.append(a)

    return render_template(
        "appointments/adoctor.html",
        pending=pending,
        active=active,
        history=history
    )

@app.route('/doctor/appointment/update', methods=['POST'])
def update_appointment_status():

    if session.get('role') != 'doctor':
        return redirect('/')

    appt_id = request.form.get('appointment_id')
    action = request.form.get('action')

    if action not in ['confirmed', 'cancelled']:
        return redirect('/doctor/appointments')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE appointments
        SET status = ?
        WHERE id = ?
    """, (action, appt_id))

    conn.commit()
    conn.close()

    return redirect('/doctor/appointments')


@app.route('/doctor/records')
@app.route('/doctor/medical-records')
def medical_records_workbench():

    if session.get('role') != 'doctor':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM doctors WHERE user_id=?", (user_id,))
    doctor = cur.fetchone()

    if not doctor:
        conn.close()
        return redirect('/')

    doctor_id = doctor['id']

    cur.execute("""
        SELECT 
            a.id,
            a.appointment_time,
            a.reason,
            u.name AS patient_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN users u ON u.id = p.user_id
        WHERE a.doctor_id = ? AND a.status = 'confirmed'
        ORDER BY a.appointment_time DESC
    """, (doctor_id,))

    appointments = cur.fetchall()
    conn.close()

    selected_id = request.args.get('appointment_id')

    return render_template(
        "medical_records/med-doc.html",
        appointments=appointments,
        selected_id=selected_id
    )



@app.route('/doctor/medical-records/submit', methods=['POST'])
def submit_medical_record():

    if session.get('role') != 'doctor':
        return redirect('/')

    appointment_id = request.form.get('appointment_id')
    symptoms = request.form.get('symptoms')
    diagnosis = request.form.get('diagnosis')
    prescription = request.form.get('prescription_notes')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT patient_id, doctor_id, status, consultation_fee, appointment_time
        FROM appointments
        WHERE id = ?
    """, (appointment_id,))

    appt = cur.fetchone()

    if not appt or appt['status'] != 'confirmed':
        conn.close()
        flash("Invalid appointment or already processed", "danger")
        return redirect('/doctor/medical-records')

    cur.execute("""
        INSERT INTO medical_records
        (patient_id, doctor_id, appointment_id, diagnosis, prescription_notes)
        VALUES (?, ?, ?, ?, ?)
    """, (
        appt['patient_id'],
        appt['doctor_id'],
        appointment_id,
        diagnosis,
        prescription
    ))

    cur.execute("""
        INSERT INTO bills
        (patient_id, doctor_id, appointment_id, total_amount, status)
        VALUES (?, ?, ?, ?, 'unpaid')
    """, (
        appt['patient_id'],
        appt['doctor_id'],
        appointment_id,
        appt['consultation_fee']
    ))

    appointment_time = appt['appointment_time'].replace("T", " ")

    month = int(appointment_time[5:7])
    year = int(appointment_time[0:4])

    cur.execute("""
        SELECT user_id, per_day_salary
        FROM doctors
        WHERE id=?
    """, (appt['doctor_id'],))

    doctor = cur.fetchone()

    doctor_user_id = doctor['user_id']
    per_day_salary = doctor['per_day_salary']

    month_key = f"{year:04d}-{month:02d}"

    cur.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE user_id=?
        AND status='present'
        AND substr(date,1,7)=?
    """, (doctor_user_id, month_key))

    present_days = cur.fetchone()[0]

    cur.execute("""
        INSERT OR IGNORE INTO salary_slips (
            user_id,
            month,
            year,
            per_day_salary,
            present_days,
            appointment_earnings,
            deductions,
            bonus,
            net_salary,
            status
        )
        VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 'pending')
    """, (
        doctor_user_id,
        month,
        year,
        per_day_salary,
        present_days
    ))

    cur.execute("""
        UPDATE salary_slips
        SET appointment_earnings = appointment_earnings + ?
        WHERE user_id=? AND month=? AND year=?
    """, (
        appt['consultation_fee'],
        doctor_user_id,
        month,
        year
    ))

    cur.execute("""
        SELECT
            per_day_salary,
            present_days,
            appointment_earnings,
            bonus,
            deductions
        FROM salary_slips
        WHERE user_id=? AND month=? AND year=?
    """, (
        doctor_user_id,
        month,
        year
    ))

    slip = cur.fetchone()

    net_salary = (
        (slip['per_day_salary'] * slip['present_days'])
        + slip['appointment_earnings']
        + slip['bonus']
        - slip['deductions']
    )

    cur.execute("""
        UPDATE salary_slips
        SET net_salary=?
        WHERE user_id=? AND month=? AND year=?
    """, (
        net_salary,
        doctor_user_id,
        month,
        year
    ))

    cur.execute("""
        UPDATE appointments
        SET status='completed'
        WHERE id=?
    """, (appointment_id,))

    conn.commit()
    conn.close()

    flash("Medical record saved successfully", "success")

    return redirect('/doctor/records')

@app.route('/doctor/my-patients')
def doctor_my_patients():

    if session.get('role') != 'doctor':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM doctors WHERE user_id=?", (user_id,))
    doctor = cur.fetchone()

    if not doctor:
        conn.close()
        return redirect('/')

    doctor_id = doctor['id']

    cur.execute("""
        SELECT 
            u.id AS user_id,
            u.name,
            u.email,
            COUNT(a.id) AS total_visits,
            MAX(a.appointment_time) AS last_visit
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN users u ON u.id = p.user_id
        WHERE a.doctor_id = ? AND a.status = 'completed'
        GROUP BY u.id
        ORDER BY last_visit DESC
    """, (doctor_id,))

    patients = cur.fetchall()

    conn.close()

    return render_template("medical_records/my_patients.html", patients=patients)

@app.route('/doctor/patient/<int:user_id>/history')
def doctor_patient_history(user_id):

    if session.get('role') != 'doctor':
        return redirect('/')

    doctor_user = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM doctors WHERE user_id=?", (doctor_user,))
    doctor = cur.fetchone()

    if not doctor:
        conn.close()
        return redirect('/')

    doctor_id = doctor['id']

    cur.execute("""
        SELECT 
            mr.diagnosis,
            mr.prescription_notes,
            a.appointment_time
        FROM medical_records mr
        JOIN appointments a ON a.id = mr.appointment_id
        WHERE mr.patient_id = (
            SELECT id FROM patients WHERE user_id = ?
        )
        AND mr.doctor_id = ?
        ORDER BY a.appointment_time DESC
    """, (user_id, doctor_id))

    records = cur.fetchall()

    conn.close()

    return render_template("medical_records/patient_history.html", records=records)



@app.route('/attendance')
def attendance_page():

    if session.get('role') not in ['doctor', 'staff']:
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM attendance
        WHERE user_id=?
        ORDER BY date DESC
    """, (user_id,))

    records = cur.fetchall()
    cur.execute("""
    SELECT * FROM leaves
    WHERE user_id=?
    ORDER BY created_at DESC
""", (user_id,))

    leaves = cur.fetchall()
    conn.close()


    return render_template(
        "attendance/attendance.html",
        records=records,
        leaves=leaves
    )
    



@app.route('/apply-leave', methods=['POST'])
def apply_leave():

    if session.get('role') not in ['doctor', 'staff']:
        return redirect('/')

    user_id = session.get('user_id')

    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    reason = request.form.get('reason')

    today = datetime.date.today().isoformat()

    if from_date < today:
        flash("Leave cannot start in the past")
        return redirect('/attendance')

    if to_date < from_date:
        flash("Invalid date range")
        return redirect('/attendance')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO leaves (user_id, from_date, to_date, reason, status)
        VALUES (?, ?, ?, ?, 'pending')
    """, (user_id, from_date, to_date, reason))

    conn.commit()
    conn.close()

    flash("Leave request submitted")
    return redirect('/attendance')

import calendar


def month_key(year, month):
    return f"{year:04d}-{month:02d}"


def calculate_attendance_salary(base_salary, present_days, total_days):

    if total_days <= 0:
        return 0

    return round((base_salary / total_days) * present_days, 2)


@app.route('/admin/salary', methods=['GET', 'POST'])
def admin_salary():

    if session.get('role') != 'admin':
        return redirect('/')

    today = datetime.date.today()

    month = request.values.get('month')
    year = request.values.get('year')

    month = int(month) if month and month != 'None' else today.month
    year = int(year) if year and year != 'None' else today.year

    role_filter = request.values.get('role', 'doctor')

    ym = month_key(year, month)

    conn = get_connection()
    cur = conn.cursor()

    payroll = []

    # ================= DOCTORS =================

    if role_filter == 'doctor':

        cur.execute("""
            SELECT
                d.id,
                d.user_id,
                d.per_day_salary,
                d.consultation_fee,
                u.name
            FROM doctors d
            JOIN users u ON u.id = d.user_id
            WHERE u.role = 'doctor'
            ORDER BY u.name
        """)

        doctors = cur.fetchall()

        for doctor in doctors:

            cur.execute("""
                SELECT COUNT(*)
                FROM attendance
                WHERE user_id=?
                AND status='present'
                AND substr(date,1,7)=?
            """, (doctor['user_id'], ym))

            present_days = cur.fetchone()[0]

            attendance_salary = (
                doctor['per_day_salary'] *
                present_days
            )

            cur.execute("""
                SELECT COUNT(*)
                FROM appointments
                WHERE doctor_id=?
                AND status='completed'
                AND substr(appointment_time,1,7)=?
            """, (doctor['id'], ym))

            completed_appointments = cur.fetchone()[0]

            appointment_earnings = (
                completed_appointments *
                doctor['consultation_fee']
            )

            net_salary = (
                attendance_salary +
                appointment_earnings
            )

            payroll.append({
                "user_id": doctor['user_id'],
                "name": doctor['name'],
                "role": "Doctor",
                "present_days": present_days,
                "appointment_earnings": appointment_earnings,
                "per_day_salary": doctor['per_day_salary'],
                "net_salary": net_salary
            })

    # ================= STAFF =================

    else:

        cur.execute("""
            SELECT
                s.id,
                s.user_id,
                s.per_day_salary,
                u.name
            FROM staff s
            JOIN users u ON u.id = s.user_id
            WHERE u.role = 'staff'
            ORDER BY u.name
        """)

        staff_members = cur.fetchall()

        for staff in staff_members:

            cur.execute("""
                SELECT COUNT(*)
                FROM attendance
                WHERE user_id=?
                AND status='present'
                AND substr(date,1,7)=?
            """, (staff['user_id'], ym))

            present_days = cur.fetchone()[0]

            net_salary = (
                staff['per_day_salary'] *
                present_days
            )

            payroll.append({
                "user_id": staff['user_id'],
                "name": staff['name'],
                "role": "Staff",
                "present_days": present_days,
                "appointment_earnings": 0,
                "per_day_salary": staff['per_day_salary'],
                "net_salary": net_salary
            })

    # ================= GENERATE / UPDATE SLIPS =================

    if request.method == 'POST':

        for row in payroll:

            cur.execute("""
                INSERT INTO salary_slips (
                    user_id,
                    month,
                    year,
                    per_day_salary,
                    appointment_earnings,
                    present_days,
                    net_salary,
                    total_paid,
                    status
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')

                ON CONFLICT(user_id, month, year)

                DO UPDATE SET

                    per_day_salary=excluded.per_day_salary,
                    appointment_earnings=excluded.appointment_earnings,
                    present_days=excluded.present_days,
                    net_salary=excluded.net_salary
            """, (

                row['user_id'],
                month,
                year,
                row['per_day_salary'],
                row['appointment_earnings'],
                row['present_days'],
                row['net_salary'],
                0

            ))

        conn.commit()

        flash("Salary slips generated successfully")

    # ================= FETCH SLIPS =================

    cur.execute("""
        SELECT
            ss.*,
            u.name
        FROM salary_slips ss
        JOIN users u ON u.id = ss.user_id
        WHERE ss.month=?
        AND ss.year=?
        AND u.role=?
        ORDER BY u.name
    """, (month, year, role_filter))

    slips_raw = cur.fetchall()

    slips = []

    for slip in slips_raw:

        total_paid = slip['total_paid'] or 0

        remaining_due = (
            slip['net_salary'] - total_paid
        )

        slip = dict(slip)

        slip['remaining_due'] = remaining_due

        if remaining_due <= 0:
            slip['status'] = 'paid'
        else:
            slip['status'] = 'pending'

        slips.append(slip)

    conn.close()

    return render_template(
        'salary/admin_salary.html',
        payroll=payroll,
        slips=slips,
        month=month,
        year=year,
        role_filter=role_filter
    )


@app.route('/admin/salary/pay/<int:salary_id>')
def pay_salary(salary_id):

    if session.get('role') != 'admin':
        return redirect('/')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            net_salary,
            total_paid
        FROM salary_slips
        WHERE id=?
    """, (salary_id,))

    slip = cur.fetchone()

    if slip:

        total_paid = slip['total_paid'] or 0

        remaining_due = (
            slip['net_salary'] - total_paid
        )

        if remaining_due <= 0:

            flash("Salary already fully paid")

        else:

            updated_total = (
                total_paid + remaining_due
            )

            cur.execute("""
                UPDATE salary_slips
                SET
                    total_paid=?,
                    paid_at=datetime('now')
                WHERE id=?
            """, (

                updated_total,
                salary_id

            ))

            conn.commit()

            flash(f"Paid remaining ₹ {remaining_due}")

    conn.close()

    return redirect(request.referrer or '/admin/salary')
@app.route('/doctor/salary')
def doctor_salary():

    if session.get('role') != 'doctor':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        ss.month,
        ss.year,
        ss.present_days,
        ss.per_day_salary,
        ss.appointment_earnings,
        ss.net_salary,
        ss.status
    FROM salary_slips ss
    WHERE ss.user_id=?
    ORDER BY ss.year DESC, ss.month DESC
""", (user_id,))

    salary_slips = cur.fetchall()

    cur.execute("""
        SELECT COALESCE(SUM(net_salary),0)
        FROM salary_slips
        WHERE user_id=? AND status='paid'
    """, (user_id,))
    total_paid = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(net_salary),0)
        FROM salary_slips
        WHERE user_id=? AND status='pending'
    """, (user_id,))
    total_pending = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE d.user_id=? AND a.status='completed'
    """, (user_id,))
    total_completed = cur.fetchone()[0]

    conn.close()

    return render_template(
        'salary/doctor_salary.html',
        salary_slips=salary_slips,
        total_paid=total_paid,
        total_pending=total_pending,
        total_completed=total_completed
    )

@app.route('/doctor/profile', methods=['GET', 'POST'])
def doctor_profile():

    if session.get('role') != 'doctor':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        specialization = request.form.get('specialization')
        consultation_fee = request.form.get('consultation_fee')
        experience_years = request.form.get('experience_years')
        license_number = request.form.get('license_number')

        cur.execute("""
            UPDATE users
            SET
                name=?,
                email=?,
                phone=?,
                address=?
            WHERE id=?
        """, (
            name,
            email,
            phone,
            address,
            user_id
        ))

        cur.execute("""
            UPDATE doctors
            SET
                specialization=?,
                consultation_fee=?,
                experience_years=?,
                license_number=?
            WHERE user_id=?
        """, (
            specialization,
            consultation_fee,
            experience_years,
            license_number,
            user_id
        ))

        conn.commit()

        flash("Profile updated successfully")

        return redirect('/doctor/profile')

    cur.execute("""
        SELECT
            u.username,
            u.name,
            u.email,
            u.phone,
            u.address,
            u.created_at,
            d.specialization,
            d.consultation_fee,
            d.per_day_salary,
            d.license_number,
            d.experience_years,
            dep.name AS department_name
        FROM users u
        JOIN doctors d ON d.user_id = u.id
        LEFT JOIN departments dep ON dep.id = d.department_id
        WHERE u.id=?
    """, (user_id,))

    doctor = cur.fetchone()

    conn.close()

    return render_template(
        'profile/doctor_profile.html',
        doctor=doctor
    )






@app.route('/doctor/profile/update', methods=['POST'])
def update_doctor_profile():

    if session.get('role') != 'doctor':
        return redirect('/')

    user_id = session.get('user_id')

    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')


    if phone and (not phone.isdigit() or len(phone) != 10):
        flash("Phone number must be exactly 10 digits")
        return redirect('/doctor/profile')
    address = request.form.get('address')

    specialization = request.form.get('specialization')
    consultation_fee = request.form.get('consultation_fee')
    experience_years = request.form.get('experience_years')
    license_number = request.form.get('license_number')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET
            name=?,
            email=?,
            phone=?,
            address=?
        WHERE id=?
    """, (
        name,
        email,
        phone,
        address,
        user_id
    ))

    cur.execute("""
        UPDATE doctors
        SET
            specialization=?,
            consultation_fee=?,
            experience_years=?,
            license_number=?
        WHERE user_id=?
    """, (
        specialization,
        consultation_fee,
        experience_years,
        license_number,
        user_id
    ))

    conn.commit()
    conn.close()

    flash("Profile updated successfully")

    return redirect('/doctor/profile')


@app.route('/staff/profile', methods=['GET', 'POST'])
def staff_profile():

    if session.get('role') != 'staff':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        designation = request.form.get('designation')
        shift_type = request.form.get('shift_type')

        if phone and (not phone.isdigit() or len(phone) != 10):
            flash("Phone number must be exactly 10 digits")
            return redirect('/staff/profile')

        cur.execute("""
            UPDATE users
            SET name=?, email=?, phone=?, address=?
            WHERE id=?
        """, (name, email, phone, address, user_id))

        cur.execute("""
            UPDATE staff
            SET designation=?, shift_type=?
            WHERE user_id=?
        """, (designation, shift_type, user_id))

        conn.commit()

        flash("Profile updated successfully")
        return redirect('/staff/profile')

    cur.execute("""
        SELECT u.username, u.name, u.email, u.phone, u.address,
               s.designation, s.per_day_salary, s.shift_type,
               d.name AS department_name
        FROM users u
        JOIN staff s ON s.user_id = u.id
        LEFT JOIN departments d ON d.id = s.department_id
        WHERE u.id=?
    """, (user_id,))

    staff = cur.fetchone()

    conn.close()

    return render_template("profile/staff_profile.html", staff=staff)

@app.route('/staff/salary')
def staff_salary():

    if session.get('role') != 'staff':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            ss.month,
            ss.year,
            ss.present_days,
            ss.per_day_salary,
            ss.net_salary,
            ss.status,
            u.name
        FROM salary_slips ss
        JOIN users u ON u.id = ss.user_id
        WHERE ss.user_id=?
        ORDER BY ss.year DESC, ss.month DESC
    """, (user_id,))

    salary_slips = cur.fetchall()

    cur.execute("""
        SELECT COALESCE(SUM(net_salary),0)
        FROM salary_slips
        WHERE user_id=? AND status='paid'
    """, (user_id,))

    total_paid = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(net_salary),0)
        FROM salary_slips
        WHERE user_id=? AND status='pending'
    """, (user_id,))

    total_pending = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE user_id=? AND status='present'
    """, (user_id,))

    total_present = cur.fetchone()[0]

    conn.close()

    return render_template(
        "salary/staff_salary.html",
        salary_slips=salary_slips,
        total_paid=total_paid,
        total_pending=total_pending,
        total_present=total_present
    )



@app.route('/admin/attendance', methods=['GET'])
def admin_attendance():

    if session.get('role') != 'admin':
        return redirect('/')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, role
        FROM users
        WHERE role IN('doctor','staff')
        ORDER BY name
    """)
    users = cur.fetchall()

    user_id = request.args.get('user_id')

    attendance = []
    leaves_pending = []
    leaves_history = []

    if user_id and user_id.isdigit():
        user_id = int(user_id)

        cur.execute("""
            SELECT date, status
            FROM attendance
            WHERE user_id = ?
            ORDER BY date DESC
        """, (user_id,))
        attendance = cur.fetchall()

        cur.execute("""
            SELECT id, from_date, to_date, reason
            FROM leaves
            WHERE user_id = ? AND status = 'pending'
            ORDER BY id DESC
        """, (user_id,))
        leaves_pending = cur.fetchall()

        cur.execute("""
            SELECT id, from_date, to_date, reason, status
            FROM leaves
            WHERE user_id = ? AND status != 'pending'
            ORDER BY id DESC
        """, (user_id,))
        leaves_history = cur.fetchall()

    conn.close()

    return render_template(
        "admin/attendance.html",
        users=users,
        user_id=str(user_id) if user_id else "",
        attendance=attendance,
        leaves_pending=leaves_pending,
        leaves_history=leaves_history
    )
@app.route('/admin/leave/approve/<int:leave_id>')
def approve_leave(leave_id):

    if session.get('role') != 'admin':
        return redirect('/')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, from_date, to_date
        FROM leaves
        WHERE id=?
    """, (leave_id,))
    leave = cur.fetchone()

    if not leave:
        return redirect('/admin/attendance')

    cur.execute("""
        UPDATE leaves
        SET status='approved'
        WHERE id=?
    """, (leave_id,))

    start = datetime.datetime.strptime(leave['from_date'], "%Y-%m-%d").date()
    end = datetime.datetime.strptime(leave['to_date'], "%Y-%m-%d").date()

    day = start
    while day <= end:

        cur.execute("""
            SELECT id FROM attendance
            WHERE user_id=? AND date=?
        """, (leave['user_id'], day.isoformat()))

        if cur.fetchone():
            cur.execute("""
                UPDATE attendance
                SET status='absent'
                WHERE user_id=? AND date=?
            """, (leave['user_id'], day.isoformat()))
        else:
            cur.execute("""
                INSERT INTO attendance (user_id, date, status)
                VALUES (?, ?, 'absent')
            """, (leave['user_id'], day.isoformat()))

        day += datetime.timedelta(days=1)

    conn.commit()
    conn.close()

    return redirect('/admin/attendance')




@app.route('/admin/leave/reject/<int:leave_id>')
def reject_leave(leave_id):

    if session.get('role') != 'admin':
        return redirect('/')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE leaves
        SET status='rejected'
        WHERE id=?
    """, (leave_id,))

    conn.commit()
    conn.close()

    return redirect('/admin/attendance')




@app.route('/patient/profile', methods=['GET', 'POST'])
def patient_profile():

    if session.get('role') != 'patient':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        gender = request.form.get('gender')
        blood_group = request.form.get('blood_group')
        dob = request.form.get('dob')
        emergency_contact = request.form.get('emergency_contact')

        if phone and (not phone.isdigit() or len(phone) != 10):
            flash("Phone must be 10 digits")
            return redirect('/patient/profile')

        cur.execute("""
            UPDATE users
            SET name=?, email=?, phone=?, address=?, gender=?, blood_group=?
            WHERE id=?
        """, (name, email, phone, address, gender, blood_group, user_id))

        cur.execute("""
            UPDATE patients
            SET dob=?, emergency_contact=?
            WHERE user_id=?
        """, (dob, emergency_contact, user_id))

        conn.commit()
        conn.close()

        flash("Profile updated")
        return redirect('/patient/profile')

    cur.execute("""
        SELECT u.username, u.name, u.email, u.phone, u.address,
               u.gender, u.blood_group,
               p.dob, p.emergency_contact
        FROM users u
        JOIN patients p ON p.user_id = u.id
        WHERE u.id=?
    """, (user_id,))

    patient = cur.fetchone()
    conn.close()

    return render_template("profile/patient_profile.html", patient=patient)


@app.route('/patient/bills')
def patient_bills():

    if session.get('role') != 'patient':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM patients WHERE user_id=?", (user_id,))
    patient = cur.fetchone()

    if not patient:
        conn.close()
        return redirect('/')

    cur.execute("""
        SELECT 
            b.id,
            b.total_amount,
            b.status,
            b.created_at,
            u.name AS doctor_name
        FROM bills b
        JOIN doctors d ON d.id = b.doctor_id
        JOIN users u ON u.id = d.user_id
        WHERE b.patient_id=?
        ORDER BY b.created_at DESC
    """, (patient['id'],))

    bills = cur.fetchall()

    conn.close()

    return render_template("/salary/bills.html", bills=bills)


@app.route('/patient/bill/pay/<int:bill_id>')
def pay_bill(bill_id):

    if session.get('role') != 'patient':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM patients WHERE user_id=?", (user_id,))
    patient = cur.fetchone()

    if not patient:
        conn.close()
        return redirect('/patient/bills')

    cur.execute("""
        UPDATE bills
        SET status='paid'
        WHERE id=? AND patient_id=?
    """, (bill_id, patient['id']))

    conn.commit()
    conn.close()

    return redirect('/patient/bills')




@app.route('/patient/medical-records')
def patient_medical_records():

    if session.get('role') != 'patient':
        return redirect('/')

    user_id = session.get('user_id')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM patients WHERE user_id=?", (user_id,))
    patient = cur.fetchone()

    if not patient:
        conn.close()
        return redirect('/')

    patient_id = patient['id']

    cur.execute("""
        SELECT 
            mr.id,
            mr.diagnosis,
            mr.prescription_notes,
            a.appointment_time,
            u.name AS doctor_name
        FROM medical_records mr
        JOIN appointments a ON a.id = mr.appointment_id
        JOIN doctors d ON d.id = mr.doctor_id
        JOIN users u ON u.id = d.user_id
        WHERE mr.patient_id = ?
        ORDER BY a.appointment_time DESC
    """, (patient_id,))

    records = cur.fetchall()

    conn.close()

    return render_template(
        "medical_records/patient_records.html",
        records=records
    )














if __name__ == '__main__':
    app.run(debug=True,port=5005)

