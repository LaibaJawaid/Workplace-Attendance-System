from flask import Flask, render_template, request,make_response, redirect, url_for, session, flash, jsonify
import webbrowser
from threading import Timer
import os
import sqlite3
import base64
import io
import csv
from io import StringIO
import numpy as np
from PIL import Image
from deepface import DeepFace
import pickle
from datetime import datetime, date

# db.py ko import kar rahe hain connection ke liye
import db 

app = Flask(__name__)
app.secret_key = "alisha_secret_key"

# Database path (Direct SQLite)
DB_PATH = os.path.join("database", "attendance.db")

# -----------------------------------------------------------
# 1. FACE RECOGNITION SETUP
# -----------------------------------------------------------
DATASET_DIR = "dataset"

try:
    with open("embeddings.pkl", "rb") as f:
        embeddings = pickle.load(f)
    print("✅ Embeddings loaded successfully.")
except FileNotFoundError:
    print("⚠️ WARNING: embeddings.pkl not found!")
    embeddings = {}

# Helper function database connection ke liye
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Isse hum data column name se access kar sakenge
    return conn

# ---------------- ROUTES ---------------- #

@app.route('/')
def choose_role():
    return render_template('choose_role.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'me123':
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid admin credentials!", "danger")
    return render_template('admin_login.html')

@app.route('/employee-login', methods=['GET', 'POST'])
def employee_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'employee' and password == 'me123':
            session['user'] = username
            return redirect(url_for('employee_dashboard'))
        else:
            flash("Invalid employee credentials!", "danger")
    return render_template('employee_login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('admin_login'))
    return render_template('dashboard.html')

@app.route('/employee-dashboard')
def employee_dashboard():
    if 'user' in session:
        return render_template('employee_dashboard.html')
    return redirect(url_for('employee_login'))

@app.route("/attendance") 
def mark_attendance():
    return render_template("attendance.html")

# ---------------- FACE RECOGNITION API (SQLite Version) ----------------
@app.route('/api/mark_attendance', methods=['POST'])
def api_mark_attendance():
    data = request.get_json()
    try:
        # 1. Get Data from Frontend
        image_data = data['img_data'].split(',')[1]
        att_type = data.get('attendance_type') # 'Check-In' or 'Check-Out'
        image_bytes = base64.b64decode(image_data)
        
        temp_path = "temp_capture.jpg"
        with open(temp_path, "wb") as f:
            f.write(image_bytes)

        # 2. Face Recognition
        dfs = DeepFace.find(img_path=temp_path, 
                            db_path=DATASET_DIR, 
                            model_name="Facenet", 
                            detector_backend="opencv", 
                            enforce_detection=False, 
                            distance_metric="cosine")

        if len(dfs) > 0 and not dfs[0].empty:
            result = dfs[0]
            dist_col = [c for c in result.columns if 'cosine' in c or 'distance' in c][0]
            best_match = result.iloc[0]
            distance = best_match[dist_col]
            
            # Threshold Check
            if distance < 0.40:  
                identity_path = best_match['identity']
                recognized_full_name = os.path.basename(os.path.dirname(identity_path)).strip()
                
                conn = get_db_connection()
                cur = conn.cursor()
                
                search_name = recognized_full_name.lower().strip()
                cur.execute('SELECT * FROM employees WHERE LOWER(TRIM("Employee Name")) = ?', (search_name,))
                emp = cur.fetchone()
                
                if emp:
                    actual_name = emp['Employee Name']
                    actual_id = emp['Employee ID']
                    dept = emp['Department']
                    today = datetime.now().strftime("%Y-%m-%d")
                    time_now = datetime.now().strftime("%H:%M:%S")

                    # --- CHECK-IN / CHECK-OUT LOGIC ---
                    cur.execute("SELECT * FROM attendance WHERE employee_code = ? AND date = ?", (actual_id, today))
                    existing_record = cur.fetchone()

                    if att_type == 'Check-In':
                        if existing_record and existing_record['check_in']:
                            # Pehle se Check-In hai
                            return jsonify({
                                "status": "already", 
                                "name": actual_name, 
                                "emp_id": actual_id, 
                                "time": time_now, 
                                "marked_time": existing_record['check_in']
                            })
                        
                        # Naya Check-In Record
                        cur.execute("""
                            INSERT INTO attendance (employee_code, name, department, check_in, date, status) 
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (actual_id, actual_name, dept, time_now, today, "Present"))
                        
                    elif att_type == 'Check-Out':
                        if existing_record and existing_record['check_out']:
                            # Pehle se Check-Out hai
                            return jsonify({
                                "status": "already", 
                                "name": actual_name, 
                                "emp_id": actual_id, 
                                "time": time_now, 
                                "marked_time": existing_record['check_out']
                            })
                        
                       # Is line ko dhundein aur badal dein:
                        if existing_record:
                      # Update Existing Record with Check-Out and Change Status
                            cur.execute("UPDATE attendance SET check_out = ?, status = 'Checked Out' WHERE employee_code = ? AND date = ?", 
                                       (time_now, actual_id, today))
                        else:
                            # Direct Check-Out (Agar subah in nahi kiya tha)
                            cur.execute("""
                                INSERT INTO attendance (employee_code, name, department, check_out, date, status) 
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (actual_id, actual_name, dept, time_now, today, "Present"))

                    conn.commit()
                    conn.close()
                    
                    # Success Response (Green Screen ke liye)
                    return jsonify({
                        "status": "success", 
                        "name": actual_name, 
                        "emp_id": actual_id, 
                        "time": time_now
                    })
                
                conn.close()

        return jsonify({"status": "error", "message": "Face not recognized."})

    except Exception as e:
        print(f"SERVER ERROR: {e}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"})
# Route 2: Ye Dashboard ko Data supply karega (API)
@app.route('/api/attendance_log')
def api_attendance_log():
    conn = get_db_connection()
    # SQL Query: check_out aur date lazmi shamil hon
    query = """
    SELECT 
        e."Employee ID", 
        e."Employee Name", 
        e."Department", 
        a.status, 
        a.check_in,
        a.check_out,
        a.date
    FROM employees e
    INNER JOIN attendance a ON e."Employee ID" = a.employee_code 
    ORDER BY a.date DESC, a.check_in DESC
    """
    rows = conn.execute(query).fetchall()
    conn.close()

    log_data = {}

    for row in rows:
        record_date = row['date']
        if record_date not in log_data:
            log_data[record_date] = {}
        
        # Status logic: Agar check-out ka time hai toh status change dikhayen
        display_status = row['status'] if row['status'] else "Present"
        if row['check_out'] and row['check_out'] != "--:--":
            display_status = "Checked Out"

        log_data[record_date][row['Employee ID']] = {
            "name": row['Employee Name'],
            "department": row['Department'] if row['Department'] else "Other",
            "status": display_status,
            "check_in": row['check_in'] if row['check_in'] else "--:--",
            "check_out": row['check_out'] if row['check_out'] else "--:--" 
        }
    return jsonify(log_data)
@app.route('/help_center') # Spelling dashboard ke link se match honi chahiye
def help_center():
    return render_template('help_center.html')

@app.route('/department_info')
def department_info():
    conn = get_db_connection()
    query = """
    SELECT e."Employee Name", e."Department", a.status 
    FROM employees e 
    LEFT JOIN attendance a ON e."Employee ID" = a.employee_code 
    AND a.date = DATE('now')
    """
    rows = conn.execute(query).fetchall()
    
    # Data ko Department ke hisab se group karna
    dept_data = {}
    for row in rows:
        dept_name = row['department'] if row['department'] else "Other"
        if dept_name not in dept_data:
            dept_data[dept_name] = []
        
        dept_data[dept_name].append({
            'name': row['Employee Name'],
            'status': row['status'] if row['status'] else "Absent"
        })
    
    conn.close()
    # Yahan file ka naam 'depart.html' rakhein kyunke aapka route wahi mang raha hai
    return render_template('depart.html', dept_data=dept_data)


@app.route('/employee_summary')
def employee_summary():
    if 'user' not in session:
        return redirect(url_for('employee_login'))
    
    # Ye sirf page load karega, data niche wale API (/api/attendance_log) se aayega
    return render_template('emp_summary.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('choose_role'))

# ---------------- ADMIN PAGES (SQLite Version) ----------------

@app.route('/departments')
def departments():
    if 'user' not in session: return redirect(url_for('admin_login'))
    conn = get_db_connection()
    depts = conn.execute("SELECT * FROM departments").fetchall() # Make sure table exists
    conn.close()
    return render_template('departments.html', departments=depts)

@app.route('/add_department', methods=['POST'])
def add_department():
    name = request.form.get('name')
    if name:
        conn = get_db_connection()
        conn.execute("INSERT INTO departments (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        flash(f"Department '{name}' added!", "success")
    return redirect(url_for('departments'))

# Department Edit karne ke liye
# Department Edit - Ise theek karein
@app.route('/edit_department/<int:id>', methods=['POST'])
def edit_department(id):
    if 'user' not in session: return redirect(url_for('admin_login'))
    name = request.form.get('name')
    if name:
        conn = get_db_connection()
        # Yahan departments table update hona chahiye
        conn.execute("UPDATE departments SET name = ? WHERE id = ?", (name, id))
        conn.commit()
        conn.close()
        flash("Department updated successfully!", "success")
    return redirect(url_for('departments'))

# Department Delete - Ise theek karein
@app.route('/delete_department/<int:id>', methods=['POST'])
def delete_department(id):
    if 'user' not in session: return redirect(url_for('admin_login'))
    conn = get_db_connection()
    # Yahan departments table se delete hona chahiye
    conn.execute('DELETE FROM departments WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("Department deleted successfully!", "danger")
    return redirect(url_for('departments'))


@app.route('/attendance_summary')
def attendance_summary():
    if 'user' not in session:
        return redirect(url_for('admin_login'))
    # Sirf file load hogi, data JavaScript fetch karega
    return render_template('att_summary.html')



@app.route('/employees')
def employees():
    if 'user' not in session: return redirect(url_for('admin_login'))
    conn = get_db_connection()
    # Ye line lazmi add karein taake data dictionary ki tarah fetch ho
    conn.row_factory = sqlite3.Row 
    all_emp = conn.execute("SELECT * FROM employees").fetchall()
    conn.close()
    return render_template('employees.html', employees=all_emp)
@app.route('/add_employee/basic', methods=['GET', 'POST'])
def add_employee_basic():
    if 'user' not in session: return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        # Form se data le kar session mein save karein
        session['basic_info'] = {
            'employee_id': request.form.get('employee_id'),
            'full_name': request.form.get('full_name')
        }
        return redirect(url_for('add_employee_job')) 

    # --- AUTO GENERATE ID LOGIC (For GET Request) ---
    conn = get_db_connection() # Connection yahan open karein
    last_emp = conn.execute('SELECT "Employee ID" FROM employees ORDER BY rowid DESC LIMIT 1').fetchone()
    conn.close()

    if last_emp:
        last_id = last_emp['Employee ID']
        try:
            # ID se number nikal kar +1 karna
            number_part = int(''.join(filter(str.isdigit, last_id))) 
            new_id = f"EMP{str(number_part + 1).zfill(3)}"
        except:
            new_id = "EMP001"
    else:
        new_id = "EMP001"
    
    # "next_id=new_id" lazmi likhna hai taake HTML mein value dikhe
    return render_template('add_employee_basic.html', next_id=new_id)

@app.route('/add_employee/job', methods=['GET', 'POST'])
def add_employee_job():
    if 'user' not in session: return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        session['job_info'] = {
            'department_id': request.form.get('department_id'), # HTML name se match karein
            'designation': request.form.get('designation'),
            'joining_date': request.form.get('joining_date')
        }
        return redirect(url_for('add_employee_contact'))

    # DATABASE SE DEPARTMENTS BHEJEIN TAAKE DROPDOWN MEIN DIKHEIN
    conn = get_db_connection()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    
    return render_template('add_employee_job.html', departments=depts)

@app.route('/add_employee/contact', methods=['GET', 'POST'])
def add_employee_contact():
    if 'user' not in session: 
        return redirect(url_for('admin_login'))

    # Jab user form submit kare (Pictures capture karne ke baad)
    if request.method == 'POST':
        try:
            # 1. Session se data uthayen
            basic = session.get('basic_info', {})
            job = session.get('job_info', {})

            # 2. Form se naya data
            email = request.form.get('email')
            phone = request.form.get('phone')
            address = request.form.get('address')
            
            emp_id = basic.get('employee_id')
            full_name = basic.get('full_name')

            if not emp_id or not full_name:
                flash("Error: Basic information missing. Start again.", "danger")
                return redirect(url_for('add_employee_basic'))

            # 3. Dataset Folder Setup
            emp_folder = os.path.join(DATASET_DIR, full_name)
            if not os.path.exists(emp_folder):
                os.makedirs(emp_folder)

            # 4. Images Save karna
            for i in range(1, 5):
                img_data = request.form.get(f'image{i}')
                if img_data and ',' in img_data:
                    header, encoded = img_data.split(",", 1)
                    data = base64.b64decode(encoded)
                    file_path = os.path.join(emp_folder, f"{full_name}_{i}.jpg")
                    with open(file_path, "wb") as f:
                        f.write(data)

            # 5. Database mein Save karna
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO employees (
                    "Employee ID", "Employee Name", "Department", 
                    "Designation", "Join Date", "Email", "Phone", "Address"
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                emp_id, full_name, job.get('department_id'), 
                job.get('designation'), job.get('joining_date'),
                email, phone, address
            ))
            conn.commit()

            # --- CRITICAL STEP FOR DEEPFACE ---
            # DeepFace ki purani representations file delete karein takay naya banda recognize ho sakay
            pkl_path = os.path.join(DATASET_DIR, "representations_facenet.pkl") # ya jo bhi aapka model name hai
            if os.path.exists(pkl_path):
                os.remove(pkl_path)
            # ----------------------------------

            conn.close()

            # 6. Cleanup
            session.pop('basic_info', None)
            session.pop('job_info', None)
            
            flash(f"Employee {full_name} added successfully!", "success")
            return redirect(url_for('employees'))

        except Exception as e:
            print(f"Error saving employee: {e}")
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('add_employee_contact'))

    # Agar GET request hai (yaani sirf page khul raha hai)
    return render_template('add_employee_contact.html')

# Employee Edit karne ka route
@app.route('/edit_employee/<path:id>')  # <--- path:id lazmi use karein
def edit_employee(id):
    if 'user' not in session: return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row 
    
    # "Employee ID" quotes mein kyunke space hai
    emp = conn.execute('SELECT * FROM employees WHERE "Employee ID" = ?', (id,)).fetchone()
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    
    if emp:
        return render_template('edit_employee.html', emp=emp, departments=depts)
    return "Employee Not Found", 404

# Update karne ka naya POST route
@app.route('/update_employee', methods=['POST'])
def update_employee():
    if 'user' not in session: return redirect(url_for('admin_login'))
    
    # Form se data uthana
    emp_code = request.form.get('employee_code')
    
    # Ye lazmi check karein ke sab names wahi hon jo HTML ke 'name' attribute mein hain
    data = (
        request.form.get('full_name'),
        request.form.get('father_name'),
        request.form.get('dob'),
        request.form.get('gender'),
        request.form.get('department'),
        request.form.get('designation'),
        request.form.get('employee_type'),
        request.form.get('joining_date'),
        request.form.get('salary'),
        request.form.get('email'),
        request.form.get('phone'),
        request.form.get('address'),
        emp_code # WHERE clause ke liye
    )
    
    conn = get_db_connection()
    try:
        conn.execute("""
            UPDATE employees 
            SET "Employee Name" = ?, "Father name" = ?, "Date of Birth" = ?, "Gender" = ?, 
                "Department" = ?, "Designation" = ?, "Employee Type" = ?, 
                "Join Date" = ?, "Salary" = ?, "Email" = ?, "Phone" = ?, "Address" = ?
            WHERE "Employee ID" = ?
        """, data)
        conn.commit()
        flash(f"Employee {emp_code} updated successfully!", "success")
    except Exception as e:
        print(f"Update Error: {e}") # Debugging ke liye terminal mein error dikhayega
        flash("Update failed. Please check database columns.", "danger")
    finally:
        conn.close()
        
    return redirect(url_for('employees'))
# Employee Delete karne ka route
@app.route('/delete_employee/<id>')
def delete_employee(id):
    if 'user' not in session: return redirect(url_for('admin_login'))
    conn = get_db_connection()
    # "Employee ID" quotes mein likhna zaroori hai
    conn.execute('DELETE FROM employees WHERE "Employee ID" = ?', (id,))
    conn.commit()
    conn.close()
    flash("Employee deleted successfully!", "danger")
    return redirect(url_for('employees'))


@app.route('/reports')
def reports():
    conn = get_db_connection()
    # Departments ki list nikalna dropdown ke liye
    depts = conn.execute("SELECT * FROM departments").fetchall()
    conn.close()
    return render_template('reports.html', departments=depts)


@app.route('/download_report', methods=['POST'])
def download_report():
    selected_dept = request.form.get('department')
    conn = get_db_connection()
    conn.row_factory = None 
    
    si = StringIO()
    cw = csv.writer(si)

    if selected_dept == "Attendance_All":
        # LEFT JOIN use kar rahe hain taaki saare employees ayen
        # Agar attendance table mein record nahi milega to Status 'Absent' dikhayega
        query = '''
            SELECT 
                e."Employee ID", 
                e."Employee Name", 
                e."Department", 
                COALESCE(a.check_in, '---') as check_in, 
                COALESCE(a.check_out, '---') as check_out, 
                COALESCE(a.date, date('now')) as date,
                CASE WHEN a.status IS NULL THEN 'Absent' ELSE a.status END as status
            FROM employees e
            LEFT JOIN attendance a ON e."Employee ID" = a.employee_code 
            AND a.date = date('now')
            ORDER BY e."Department" ASC
        '''
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        
        cw.writerow(['Employee ID', 'Employee Name', 'Department', 'Check-In', 'Check-Out', 'Date', 'Status'])
        for row in rows:
            cw.writerow(list(row))
        
        filename = "Daily_Attendance_Summary.csv"

    else:
        # Baki reports ka purana code
        if selected_dept == "All":
            cursor = conn.execute("SELECT * FROM employees")
            filename = "All_Staff_Report.csv"
        else:
            cursor = conn.execute('SELECT * FROM employees WHERE "Department"=?', (selected_dept,))
            filename = f"{selected_dept}_Staff_Report.csv"
        
        rows = cursor.fetchall()
        cw.writerow(['ID', 'Employee ID', 'Employee Name', 'Father name', 'Date of Birth', 'Gender', 'Department', 'Designation', 'Employee Type', 'Join Date', 'Salary', 'Email', 'Phone', 'Address', 'Photo'])
        
        for row in rows:
            cw.writerow(list(row))

    conn.close()
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv"
    return output

# ---------------- BROWSER & SERVER ---------------- #

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    # Tables banane ke liye db.py ka function call karein
    db.create_tables() 
    
    # Initial Data Check
    conn = get_db_connection()
    
    # Pehle purane departments check karein
    check = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
    
    # Agar 0 hain ya sirf purane 3 hain, toh unhe update kar dein
    if check <= 3:
        # Purana data clear karein taake nayi list sahi se aaye
        conn.execute("DELETE FROM departments")
        
        # Aapki di hui nayi list
        new_depts = [
            ('Human Resources',), 
            ('Finance',), 
            ('Sales',), 
            ('Marketing',), 
            ('Technology',), 
            ('Operations',)
        ]
        
        conn.executemany("INSERT INTO departments (name) VALUES (?)", new_depts)
        conn.commit()
        print("✅ Departments list updated with: HR, Finance, Sales, Marketing, Technology, Operations")
    
    conn.close()

    Timer(1, open_browser).start()
    app.run(debug=False)