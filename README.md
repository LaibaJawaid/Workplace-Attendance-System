# 🏢 Workplace Attendance System (Face Recognition Based)
**Version:** v1.0.0  
**Status:** Prototype / Initial Release  

A face recognition–based workplace attendance system built using **Flask**, **FaceNet (512-D embeddings)**, **OpenCV**, and **SQLite**.  
This version focuses on **core face recognition logic** with a manually structured backend, serving as a foundation for a more robust and scalable system in future releases.

---

## 🚀 Features (v1.0.0)

- Face-based employee attendance system
- Employee enrollment using multiple face images
- Face detection using **OpenCV Haar Cascade**
- Face embeddings using **FaceNet (512-dimension)**
- SQLite database for employee & embedding storage
- Flask-based web interface
- Manual but functional backend workflow
- Dataset organized per employee with multiple angles

---

## 🧠 Technology Stack

| Component | Technology |
|--------|-----------|
| Backend | Flask (Python) |
| Face Detection | OpenCV Haar Cascade |
| Face Embeddings | FaceNet (512-D) |
| Database | SQLite3 |
| Vector Storage | BLOB embeddings |
| Frontend | HTML / CSS (Flask Templates) |

---

## 📁 Project Structure (Current v1)
WORKPLACE_ATTENDANCE_SYSTEM/
│
├── database/ # SQLite database files
├── dataset/ # Employee face datasets
│ └── emp_<name>/ # Multiple face images per employee
│
├── templates/ # All HTML files
├── static/ # CSS / JS/assets
│
├── app.py # Main Flask app
├── db.py # Database connection logic
├── create_db.py # Database initialization
├── bulk_insert.py # Bulk employee insert
├── enroll.py # Employee enrollment logic
├── face_detect.py # Face detection using Haar Cascade
├── embed_service.py # FaceNet embedding generation
├── update_emp.py # Employee update logic
├── check_db.py # DB debugging utility
├── test.py # Testing scripts
│
├── haarcascade_frontalface_default.xml
├── Employee List face sys.csv
└── temp_capture.jpg

---

## 👤 Dataset Handling

- Each employee has a dedicated folder but due to privacy concerns, I haven't uploaded the dataset folder here but you can look at the way we structured our dataset folder as:
  
  dataset/
└── emp_Ali/
├── img1.jpg
├── img2.jpg
├── img3.jpg
└── img4.jpg

- Images are captured from **different angles** for better recognition
- Faces are resized to FaceNet’s required input size before embedding

---

## 🔍 Face Recognition Workflow (v1)

1. Capture face image
2. Detect face using Haar Cascade
3. Resize & preprocess image
4. Generate **512-D FaceNet embedding**
5. Store embedding as **BLOB in SQLite**
6. Compare embeddings using distance threshold
7. Mark attendance if matched

---

## 🤔 Why FaceNet?

- Pretrained and well-tested
- Produces high-quality **512-dimension embeddings**
- Lightweight compared to heavy transformer models
- Suitable for prototype & CPU-based systems
- Easy to integrate with Flask

---

## ⚠️ Current Limitations (v1)

- No FAISS vector indexing
- Haar Cascade is less robust than RetinaFace
- SQLite used instead of production DB
- Manual file organization
- No role-based admin/user separation
- No ONNX optimization yet
- Limited accuracy in low-light & occlusion cases

---

## 🔮 Future Improvements (v2 Roadmap)

✔ Replace Haar Cascade with **RetinaFace**  
✔ Switch FaceNet → **ArcFace (ONNX optimized)**  
✔ Add **FAISS** for fast similarity search  
✔ Introduce **SQLAlchemy ORM**  
✔ Separate **Admin & User Panels**  
✔ Proper MVC / Service-based backend  
✔ Cloud-ready deployment  
✔ Improve accuracy & performance  
✔ Secure API & authentication  

---

## 🛠 How to Run (Basic)

pip install -r requirements.txt
python create_db.py
python app.py
browser at: http://127.0.0.1:5000

----

###  How to use (Admin and Employee Panels login) :

- Employee name: employee
- Password: me123

- Admin name: admin
- Password: me123

----

## Versioning

└── v1.0.0 – Initial working prototype
└── v2.0.0 (Planned) – Production-ready architecture
Still updating for v2!

-----

## ⭐ Support
If this project helps you, ⭐ star the repo on GitHub!
-----
