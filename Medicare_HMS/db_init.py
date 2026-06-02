import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "database.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(conn, table, column):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return any(row["name"] == column for row in cur.fetchall())


def add_column_if_missing(conn, table, column, definition):
    if not column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('patient','doctor','staff','admin')),
    phone TEXT,
    address TEXT,
    gender TEXT CHECK(gender IN ('male','female','other')),
    blood_group TEXT CHECK(blood_group IN ('A+','A-','B+','B-','O+','O-','AB+','AB-')),
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

    CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    dob TEXT,
    emergency_contact TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        department_type TEXT NOT NULL CHECK(department_type IN ('doctor', 'staff'))
    );

    CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    specialization TEXT NOT NULL,
    department_id INTEGER,
    consultation_fee REAL DEFAULT 0,
    license_number TEXT UNIQUE,
    per_day_salary REAL DEFAULT 0,
    experience_years INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE SET NULL
);

    CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,

    designation TEXT,
    department_id INTEGER,

    per_day_salary REAL DEFAULT 0,
    shift_type TEXT DEFAULT 'day'
        CHECK(shift_type IN ('day', 'night', 'rotational')),

    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE SET NULL
);


    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        consultation_fee REAL DEFAULT 0,
        appointment_time TEXT NOT NULL,
        status TEXT DEFAULT 'pending'
            CHECK(status IN ('pending', 'confirmed', 'completed', 'cancelled', 'no-show')),
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
        FOREIGN KEY(doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS medical_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        appointment_id INTEGER,
        diagnosis TEXT,
        prescription_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id),
        FOREIGN KEY(doctor_id) REFERENCES doctors(id),
        FOREIGN KEY(appointment_id) REFERENCES appointments(id)
    );

    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER,
        appointment_id INTEGER,
        total_amount REAL DEFAULT 0,
        status TEXT DEFAULT 'unpaid'
            CHECK(status IN ('unpaid', 'paid', 'partial')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id),
        FOREIGN KEY(doctor_id) REFERENCES doctors(id),
        FOREIGN KEY(appointment_id) REFERENCES appointments(id)
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        check_in TIMESTAMP,
        check_out TIMESTAMP,
        status TEXT DEFAULT 'present'
            CHECK(status IN ('present', 'absent', 'half-day')),
        UNIQUE(user_id, date),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS salary_slips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        per_day_salary REAL DEFAULT 0,
        appointment_earnings REAL DEFAULT 0,
        present_days INTEGER DEFAULT 0,
        absent_days INTEGER DEFAULT 0,
        bonus REAL DEFAULT 0,
        paid_at TEXT,
        deductions REAL DEFAULT 0,
        net_salary REAL DEFAULT 0,
        total_paid INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending'
            CHECK(status IN ('pending', 'paid')),
        UNIQUE(user_id, month, year),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS leaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        from_date TEXT NOT NULL,
        to_date TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'pending'
            CHECK(status IN ('pending','approved','rejected')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    
                         





    """)

    conn.commit()

    # Migration support for existing databases
    add_column_if_missing(conn, "doctors", "consultation_fee", "REAL DEFAULT 0")
    add_column_if_missing(conn, "appointments", "consultation_fee", "REAL DEFAULT 0")
    add_column_if_missing(conn, "bills", "doctor_id", "INTEGER")
    add_column_if_missing(conn, "salary_slips", "appointment_earnings", "REAL DEFAULT 0")

    conn.commit()
    conn.close()


def create_admin():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE role='admin'")
    exists = cur.fetchone()

    if not exists:
        cur.execute("""
            INSERT INTO users (username, email, password_hash, name, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "admin",
            "admin@medicare.com",
            generate_password_hash("admin123"),
            "System Admin",
            "admin"
        ))
        conn.commit()

    conn.close()


if __name__ == "__main__":
    init_db()
    create_admin()