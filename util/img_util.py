
import cv2
import threading
import time
from queue import Queue
import os
import base64
import numpy as np


base_visitor_face_dir = "./visitor_face"
base_staff_face_dir = "./staff_face"
known_visitor_faces = {}

class CapedImgUtil:

    def process_extract_faces(self, frame, faces):
        faces_img_base64str = []
        for i, (x, y, w, h) in enumerate(faces):
            print(f"第 {i + 1} 张人脸区域: x={x}, y={y}, w={w}, h={h}")

            # 检查坐标是否在帧的范围内
            if x < 0 or y < 0 or w <= 0 or h <= 0:
                print(f"无效的人脸区域: x={x}, y={y}, w={w}, h={h}")
                continue

            # 提取人脸区域
            face_img = frame[y:y + h, x:x + w]

            # 检查提取的图像是否为空
            if face_img is None or face_img.size == 0:
                print("提取的人脸图像为空，跳过处理")
                continue
            _, img_encoded = cv2.imencode('.jpg', face_img)
            img_base64 = base64.b64encode(img_encoded).decode('utf-8')
            faces_img_base64str.append(img_base64)
            # print(f"第 {i + 1} 张人脸, img: {img_base64}")
        # face_cnt = len(faces)
        # if face_cnt > 0:
        #     print(f"共计{face_cnt} 张人脸， 原始frame: {frame}")
        return faces_img_base64str

    def frame_to_base64(self, frame):
        """
        将 OpenCV 获取的帧转换为 Base64 编码字符串

        参数:
            frame: OpenCV 的帧数据 (numpy 数组)

        返回:
            base64_str: Base64 编码的字符串
        """
        # 将帧数据编码为 JPEG 格式
        _, buffer = cv2.imencode('.jpg', frame)

        # 将编码后的数据转换为字节流
        frame_bytes = buffer.tobytes()

        # 将字节流编码为 Base64 字符串
        base64_str = base64.b64encode(frame_bytes).decode('utf-8')

        return base64_str

    def save_image_to_path(self, face_img, usr_id,  vis_time):
        img_dir = self.build_visitor_img_dir(usr_id)
        os.makedirs(img_dir, exist_ok=True)
        # 保存图片
        img_path = self.build_visitor_img_save_path_with_ts(usr_id, vis_time)
        cv2.imwrite(img_path, face_img)
        return img_path


    def save_new_visitor_in_def_path(self, face_img, usr_id):
        """
        创建新的人员信息
        """
        person_dir = self.build_visitor_img_dir(usr_id)
        os.makedirs(person_dir, exist_ok=True)

        # 保存图片
        person_img = f"visitor_{usr_id}.jpg"
        img_path = os.path.join(person_dir, person_img)
        cv2.imwrite(img_path, face_img)
        return f"{person_dir}/{person_img}"



    def build_visitor_img_save_path_with_ts(self, usr_id, vis_time):
        person_dir = self.build_visitor_img_dir(usr_id)
        person_img_name = self.build_visitor_img_name_with_ts(usr_id, vis_time)
        return f"{person_dir}/{person_img_name}"

    def build_visitor_img_enhance_save_path(self, user_id, vis_time):
        person_dir = self.build_visitor_img_dir(user_id)
        person_path_name = self.build_visitor_img_enhance_path_name(user_id, vis_time)
        return f"{person_dir}/{person_path_name}"

    def build_visitor_img_save_path_no_ts(self, usr_id):
        person_id = f"visitor_{usr_id}"
        person_dir = os.path.join(base_visitor_face_dir, person_id)
        person_img = f"{person_id}.jpg"
        return f"{person_dir}/{person_img}"

    def build_visitor_img_dir(self, usr_id):
        person_id = f"visitor_{usr_id}"
        person_dir = os.path.join(base_visitor_face_dir, person_id)
        return person_dir

    def build_visitor_img_name_with_ts(self, usr_id, vis_time):
        person_id = f"visitor_{usr_id}"
        vis_time_str = vis_time.strftime("%Y%m%d%H%M%S")
        person_img = f"{person_id}_{vis_time_str}.jpg"
        return person_img

    def build_visitor_img_enhance_path_name(self, user_id, vis_time):
        person_id = f"visitor_{user_id}"
        vis_time_str = vis_time.strftime("%Y%m%d%H%M%S")
        vis_path = f"{person_id}_{vis_time_str}_enhance"
        return vis_path

    def trans_img_base64_to_img(self, face_img):
        img_bytes = base64.b64decode(face_img)

        # 将字节数据转换为numpy数组
        img_np = np.frombuffer(img_bytes, dtype=np.uint8)

        # 使用OpenCV解码图像
        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
        return img


