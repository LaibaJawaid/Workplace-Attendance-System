from deepface import DeepFace
import cv2
import numpy as np
from face_detect import detect_face_opencv

def get_embedding(img_path):
    img = cv2.imread(img_path)

    face = detect_face_opencv(img)

    if face is None:
        # fallback: full image
        face = img

    face = cv2.resize(face, (160, 160))

    rep = DeepFace.represent(
        img_path=face,
        model_name="Facenet",
        detector_backend="skip",      # 🔥 NO internal detection
        enforce_detection=False
    )

    return np.array(rep[0]["embedding"], dtype=np.float32)
