import sqlite3
import numpy as np
import os

DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "attendance.db")

def get_connection():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

def create_tables():
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Departments Table
    cur.execute("CREATE TABLE IF NOT EXISTS departments (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")

    # 2. Employees Table (EXACT matching your CSV)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        "Employee ID" TEXT UNIQUE NOT NULL,
        "Employee Name" TEXT,
        "Father name" TEXT,
        "Date of Birth" TEXT,
        "Gender" TEXT,
        "Department" TEXT,
        "Designation" TEXT,
        "Employee Type" TEXT,
        "Join Date" TEXT,
        "Salary" TEXT,
        "Email" TEXT,
        "Phone" TEXT,
        "Address" TEXT,
        "photo" TEXT
    )
    """)

    # 3. Embeddings Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_code TEXT,
        embedding BLOB,
        FOREIGN KEY (employee_code) REFERENCES employees("Employee ID")
    )
    """)

    # 4. Attendance Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_code TEXT,
        name TEXT,
        department TEXT,
        check_in TEXT,
        check_out TEXT,
        date TEXT,
        status TEXT DEFAULT 'Present'
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Database Tables Created Successfully!")

# --- Fixed Functions to match new column names ---

def insert_employee(data):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT OR IGNORE INTO employees 
            ("Employee ID", "Employee Name", "Father name", "Date of Birth", "Gender", 
             "Department", "Designation", "Employee Type", "Join Date", "Salary", 
             "Email", "Phone", "Address", "photo")
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        conn.commit()
    finally:
        conn.close()

def fetch_employee_details(emp_code):
    conn = get_connection()
    # "Employee Name" aur "Employee ID" use karna hoga
    row = conn.execute('SELECT "Employee Name", "Department" FROM employees WHERE "Employee ID"=?', (emp_code,)).fetchone()
    conn.close()
    if row:
        return {"name": row['Employee Name'], "department": row['Department']}
    return {"name": "Unknown", "department": "Unknown"}

def mark_attendance(emp_code, name, department, date_str, time_str):
    conn = get_connection()
    cur = conn.cursor()
    # Check if already checked in today
    cur.execute("SELECT id, check_out FROM attendance WHERE employee_code=? AND date=?", (emp_code, date_str))
    row = cur.fetchone()

    if row:
        if row['check_out'] is None:
            cur.execute("UPDATE attendance SET check_out=? WHERE id=?", (time_str, row['id']))
    else:
        cur.execute("INSERT INTO attendance (employee_code, name, department, check_in, date) VALUES (?, ?, ?, ?, ?)",
                    (emp_code, name, department, time_str, date_str))
    conn.commit()
    conn.close()

# --- Common Helper Functions ---
def fetch_all_departments():
    conn = get_connection()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    return depts

if __name__ == "__main__":
    create_tables()