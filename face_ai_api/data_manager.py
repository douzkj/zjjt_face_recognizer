# data_manager.py
import os

import cv2


class DataManager:
    def __init__(self, base_dir="FaceDatabase"):
        self.base_dir = base_dir
        self.known_faces = {}
        self.current_faces = {}
        self.initialize_storage()

    def initialize_storage(self):
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        self.load_existing_data()

    def load_existing_data(self):
        for person_dir in os.listdir(self.base_dir):
            path = os.path.join(self.base_dir, person_dir)
            if os.path.isdir(path):
                self.known_faces[person_dir] = {
                    "k": len(os.listdir(path)),
                    "images": [os.path.join(path, f) for f in os.listdir(path)]
                }

    def create_new_person(self, face_img):
        person_id = f"person_{len(self.known_faces) + 1}"
        person_dir = os.path.join(self.base_dir, person_id)
        os.makedirs(person_dir, exist_ok=True)

        img_path = os.path.join(person_dir, "face_0.jpg")
        cv2.imwrite(img_path, face_img)

        self.known_faces[person_id] = {
            "k": 1,
            "images": [img_path]
        }
        self.current_faces[person_id] = True
        return person_id

    def update_person_info(self, person_id, face_img):
        if not self.current_faces.get(person_id, False):
            person_dir = os.path.join(self.base_dir, person_id)
            img_count = len(os.listdir(person_dir))
            img_path = os.path.join(person_dir, f"face_{img_count}.jpg")

            cv2.imwrite(img_path, face_img)
            self.known_faces[person_id]["k"] += 1
            self.known_faces[person_id]["images"].append(img_path)
            self.current_faces[person_id] = True