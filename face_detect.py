import cv2
import os

# Path relative to this script
cascade_path = os.path.join(os.path.dirname(__file__), "haarcascade_frontalface_default.xml")
face_cascade = cv2.CascadeClassifier(cascade_path)

if face_cascade.empty():
    raise RuntimeError(f"Haarcascade load nahi hui from {cascade_path}")

print("✅ Haarcascade loaded successfully")

def detect_face_opencv(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=3,
        minSize=(60, 60)
    )

    if len(faces) == 0:
        return None

    # largest face
    faces = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)
    x, y, w, h = faces[0]
    return img[y:y+h, x:x+w]



import sqlite3

# Connection banayein
conn = sqlite3.connect("database/attendance.db")
cur = conn.cursor()

# Query chalayein (Yahan line ke shuru mein koi space nahi honi chahiye)
cur.execute("SELECT * FROM attendance")
print(cur.fetchall())

# Connection band karein
conn.close()