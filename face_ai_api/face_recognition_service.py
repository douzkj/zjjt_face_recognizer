# face_recognition_service.py
import base64
import logging
import os
import time

import cv2
import requests

from util.img_util import CapedImgUtil

API_KEYS = {
    "TOKEN_URL": "https://aip.baidubce.com/oauth/2.0/token",
    # "API_KEY": "RRC12UOewloTFkc5hocU7Dr4",
    "API_KEY": "TDHheOu5ZzG9HLUiYNztu5ir",
    # "SECRET_KEY":  "S8V8aGoJlM9mhlF7qT7GQ12mw9rsSwTR",
    "SECRET_KEY":  "FkiDsLNbPMiHfBntTJIfiFAIMTNGLoUI",
    "REQUEST_DETECT_URL": "https://aip.baidubce.com/rest/2.0/face/v3/detect",
    "REQUEST_URL": "https://aip.baidubce.com/rest/2.0/face/v3/match",
    "REQUEST_URL_SINGLE_FACE_SEARCH": "https://aip.baidubce.com/rest/2.0/face/v3/search",
    # "REQUEST_URL_SINGLE_FACE_SEARCH": "https://xx1211xx.com",
    "REQUEST_URL_MUT_FACE_SEARCH": "https://aip.baidubce.com/rest/2.0/face/v3/multi-search",
    "SEARCH_GROUPS": "face_staff,face_visitor"
}
SEARCH_GROUP_ALL = "face_staff,face_visitor"
SEARCH_GROUP_STAFF = "face_staff"
SEARCH_GROUP_VISITOR = "face_visitor"
IMG_TYPE_BASE64 = "BASE64"

RES_ERR_CODE = "error_code"
SCORE_THRESHOLD = 80
API_ERR_EXP_CODE = -1
API_SUCC_CODE = 0
API_NOT_MATCH_FACE_CODE = 222207

capedImgUtil = CapedImgUtil()

FACE_ANGLE_THRESHOLD_YAW = os.getenv('FACE_ANGLE_THRESHOLD_YAW', 40)
# FACE_ANGLE_THRESHOLD_YAW = 40
FACE_ANGLE_THRESHOLD_PITCH = os.getenv('FACE_ANGLE_THRESHOLD_PITCH', 35)
FACE_ANGLE_THRESHOLD_ROLL = os.getenv('FACE_ANGLE_THRESHOLD_ROLL', 30)

class FaceRecognitionService:
    def __init__(self):
        self.access_token = self.get_access_token()
        self.frame = None

    def get_access_token(self):
        params = {
            "grant_type": "client_credentials",
            "client_id": API_KEYS["API_KEY"],
            "client_secret": API_KEYS["SECRET_KEY"]
        }
        response = requests.post(API_KEYS["TOKEN_URL"], params=params)
        return response.json().get("access_token")

    def detect_faces(self, frame):
        _, img_encoded = cv2.imencode('.jpg', frame)
        img_base64 = base64.b64encode(img_encoded).decode('utf-8')
        # print(f"检测===人脸:" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ", " + img_base64)
        params = {
            "image": img_base64,
            "image_type": "BASE64",
            "face_field": "location,quality",
            "max_face_num": 10
        }

        try:
            response = requests.post(
                f"{API_KEYS['REQUEST_DETECT_URL']}?access_token={self.access_token}",
                json=params,
                headers={'Content-Type': 'application/json'}
            )
            result = response.json()
            now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            res = result.get("error_code");
            print(f"检测===人脸,{now_time} , AI result:{res}")
            if result.get("error_code") == 0:
                return self.process_detection_result(frame, result)
            return frame, []
        except Exception as e:
            print(f"API异常: {str(e)}")
            return frame, []

    # 从图片中提取人脸信息（ext：待添加正脸筛选？）
    def process_detection_result(self, frame, result):
        face_list = result.get("result", {}).get("face_list", [])
        faces = []
        # print(f"人脸检测 res info:{face_list} 张人脸 ")
        for face in face_list:
            print(f"人脸检测 res info:{face}   ")
            location = face.get("location", {})
            left = int(location.get("left", 0)) - 30
            top = int(location.get("top", 0)) - 30
            width = int(location.get("width", 0)) + 60
            height = int(location.get("height", 0)) + 60

            # 检测角度是否正常，阈值内的放入到人脸集合中
            if self.check_angle_values(face):
                faces.append((left, top, width, height))
                cv2.rectangle(frame, (left, top), (left + width, top + height), (0, 255, 0), 2)
            else:
                ang_info = face.get("angle")
                print(f"人脸检测角度不满足，angle info:{ang_info} 张人脸 ")
        # _, img_encoded = cv2.imencode('.jpg', frame)
        # img_base64 = base64.b64encode(img_encoded).decode('utf-8')
        face_cnt = len(faces)
        now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # print(f"检测到 {face_cnt} 张人脸", {now_time})
        if face_cnt > 0:
            print(f"共计{face_cnt} 张人脸, {now_time}"
                  # f"， 原始frame: {capedImgUtil.frame_to_base64(frame)}"
                  f"")
        self.frame = frame
        return frame, faces

    def check_angle_values(self, json_data):
        """
        检查JSON数据中angle字段的三个属性的绝对值是否都小于给定的阈值。

        :param json_data: 包含face信息的JSON数据（字典形式）
        :param threshold: 阈值，用于比较angle属性的绝对值
        :return: 如果所有angle属性的绝对值都小于阈值，返回True；否则返回False
        """
        # 获取angle字段
        angle = json_data.get("angle")
        if not angle:
            raise ValueError("JSON数据中不存在angle字段")

        # 检查angle下的三个属性
        yaw = angle.get("yaw")
        pitch = angle.get("pitch")
        roll = angle.get("roll")

        # 检查是否存在缺失的属性
        if yaw is None or pitch is None or roll is None:
            raise ValueError("angle字段中缺少必要的属性")

        # 检查绝对值是否都小于阈值
        if abs(yaw) < FACE_ANGLE_THRESHOLD_YAW and abs(pitch) < FACE_ANGLE_THRESHOLD_PITCH and abs(roll) < FACE_ANGLE_THRESHOLD_ROLL:
            return True
        else:
            return False

    # def process_extract_faces(self, faces):
    #     faces_img_base64str = []
    #     for i, (x, y, w, h) in enumerate(faces):
    #         print(f"第 {i + 1} 张人脸区域: x={x}, y={y}, w={w}, h={h}")
    #
    #         # 检查坐标是否在帧的范围内
    #         if x < 0 or y < 0 or w <= 0 or h <= 0:
    #             print(f"无效的人脸区域: x={x}, y={y}, w={w}, h={h}")
    #             continue
    #
    #         # 提取人脸区域
    #         face_img = self.frame[y:y + h, x:x + w]
    #
    #         # 检查提取的图像是否为空
    #         if face_img is None or face_img.size == 0:
    #             print("提取的人脸图像为空，跳过处理")
    #             continue
    #         _, img_encoded = cv2.imencode('.jpg', face_img)
    #         img_base64 = base64.b64encode(img_encoded).decode('utf-8')
    #         faces_img_base64str.append(img_base64)
    #         print(f"第 {i + 1} 张人脸, img: {img_base64}")
    #     return faces_img_base64str

    def identify_person_1n(self, face_img):
        if face_img is None:
            print("人脸图像为空，跳过处理")
            return None

        # 调用 face_match 方法进行比对
        result = self.face_sing_search(face_img)
        # print(f"-----------request baidu AI processing res: {str(result)}")
        return self.parse_idety_res(result)

    def parse_idety_res(self, result):
        """
        处理解析结果，根据group_id和score进行不同操作
        :param res: 解析结果，字典格式
        :param img: 图片数据
        """
        # 调用失败/返回非可识别（code！=0）均做异常图片处理，不做后续入库或计数
        if not result or (result.get("error_code") != API_SUCC_CODE and result.get("error_code") != API_NOT_MATCH_FACE_CODE ):
            print(f"-----------request baidu AI processing res err: {str(result)}")
            return {"error_code": API_ERR_EXP_CODE}

        print(f"-----------request baidu AI processing res : {str(result)}")

        resp_code = result.get("error_code")
        if resp_code == API_NOT_MATCH_FACE_CODE:
            return

        resultVal = result.get("result", {})
        user_list = resultVal.get("user_list", [])

        if not user_list:
            # print("未找到用户信息")
            return

        user_info = user_list[0]
        group_id = user_info.get("group_id")
        usr_id = user_info.get("user_id")
        score = user_info.get("score", 0)

        if (group_id == SEARCH_GROUP_STAFF and score > SCORE_THRESHOLD) or (group_id == SEARCH_GROUP_VISITOR and score > SCORE_THRESHOLD):
            return {"user_id": usr_id, "group_id": group_id, "error_code": API_SUCC_CODE}  # 返回用户信息
        return None



    def face_match(self, image1_path, image2_path):
        image1_base64 = self.read_image(image1_path)
        image2_base64 = self.read_image(image2_path)

        params = [
            {"image": image1_base64, "image_type": "BASE64"},
            {"image": image2_base64, "image_type": "BASE64"}
        ]

        response = requests.post(
            f"{API_KEYS['REQUEST_URL']}?access_token={self.access_token}",
            json=params,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("result", {}).get("score", 0)
        return 0

    def face_sing_search(self, image_base64):
        params = {"image": image_base64,
             "image_type": IMG_TYPE_BASE64,
              "group_id_list": SEARCH_GROUP_ALL
             }

        try:
            response = requests.post(
                f"{API_KEYS['REQUEST_URL_SINGLE_FACE_SEARCH']}?access_token={self.access_token}",
                json=params,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                result = response.json()
                return result
        except Exception as e:
            logging.log(logging.ERROR, e)
            return


    #######
    '''
        人脸库管理（注册、更新、删除、组管理）
    '''
    def reg_person_face(self, face_img_base64_str, group_id, user_id):
        request_url = "https://aip.baidubce.com/rest/2.0/face/v3/faceset/user/add"
        params = {"image": face_img_base64_str,
             "image_type": IMG_TYPE_BASE64,
             "group_id": group_id,
             "user_id": user_id
             }

        request_url = request_url + "?access_token=" + self.access_token
        headers = {'content-type': 'application/json'}
        response = requests.post(request_url, data=params, headers=headers)
        if response:
            print(response.json())


    def read_image(self, file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

if __name__ == '__main__':
    face_service = FaceRecognitionService()
    token = face_service.get_access_token()
    print("-------: " + token)
