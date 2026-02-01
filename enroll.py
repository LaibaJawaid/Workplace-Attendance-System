import os
import joblib
import sqlite3
from embed_service import get_embedding
from db import insert_embedding, create_tables

DATASET_PATH = "dataset"
BACKUP_PATH = "database/embeddings_backup.joblib"
DB_PATH = "database/attendance.db"

def get_emp_code_by_name(name):
    """Folder name se Employee ID dhoondne ke liye function"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Name ko match karne ke liye query (case insensitive search)
    cur.execute("SELECT employee_code FROM employees WHERE name LIKE ?", (f"%{name}%",))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None

def enroll_all():
    create_tables()
    backup = []

    # Dataset folder ke andar har folder (jo ke employee name hai)
    for emp_name in os.listdir(DATASET_PATH):
        emp_dir = os.path.join(DATASET_PATH, emp_name)

        if not os.path.isdir(emp_dir):
            continue

        # Pehle database se is Name ki ID (EMP code) nikaal lete hain
        emp_code = get_emp_code_by_name(emp_name)
        
        if not emp_code:
            print(f"⚠️ Warning: Employee name '{emp_name}' database mein nahi mila. Skipping...")
            continue

        for img_name in os.listdir(emp_dir):
            img_path = os.path.join(emp_dir, img_name)

            try:
                emb = get_embedding(img_path)
                # Ab hum ID (EMP0001) save kar rahe hain, folder name nahi
                insert_embedding(emp_code, emb)
                backup.append((emp_code, emb))
                print(f"✅ Embedded: {emp_name} (ID: {emp_code}) -> {img_name}")
            except Exception as e:
                print(f"❌ Error {img_name}: {e}")

    joblib.dump(backup, BACKUP_PATH)
    print(f"💾 Backup saved to {BACKUP_PATH}")

if __name__ == "__main__":
    enroll_all()