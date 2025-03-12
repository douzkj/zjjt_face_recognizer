import base64
import sys
import threading
import time
from datetime import datetime
from queue import Queue
from random import Random

import cv2
import numpy as np

from dao.base_dao import TaskDAO, DB_URL, FaceIdentityTask, RecordDAO, VisitorImgDetailDAO, VisitorBaseInfoDAO, \
    VisitorTaskAggDataDAO
from dao.face_db_enty import FaceIdentityRecord, FaceVisitorBaseInfo, FaceVisitorTaskAggData
from face_ai_api.face_recognition_service import SEARCH_GROUP_STAFF, SEARCH_GROUP_VISITOR
from util.img_util import CapedImgUtil
from util.codeformer_enhancer import enhance
from util.face_enhance import send_enhance_task

test_rtsp_url="rtsp://rtspstream:WpPKtiupaLFDguY4KUlEe@zephyr.rtsp.stream/movie"

# os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;8192000"
task_dao = TaskDAO(DB_URL)
record_dao = RecordDAO(DB_URL)
visitor_detail_dao = VisitorImgDetailDAO(DB_URL)
visitor_task_agg_dao = VisitorTaskAggDataDAO(DB_URL)
visitor_base_info_dao = VisitorBaseInfoDAO(DB_URL)

VISITOR_PREFIX = "visitor_"

RANDOM = Random(int(time.time()))
capedImgUtil = CapedImgUtil()

# f = open('log.txt', 'w')
# sys.stdout = f

# RTSP拉流处理流程框架类
#1）拉流取图片帧，2）检测图片人脸正脸，3）从图片中抽取正脸后，入MQ
class RTSPStreamCapActionTmplate:
    def __init__(self, video_processor, cap_period=5, rtsp_url=test_rtsp_url):
        self.cap = None
        self.is_running = False
        self.video_processor = video_processor
        self.cap_period = cap_period  # 新增处理间隔参数
        self.rtsp_url = rtsp_url  # 新增处理间隔参数
        self.frame_queue = Queue(maxsize=100)  # 控制队列大小
        self.retry_count = 0  # 重试计数
        self.max_retry_attempts = 3  # 最大重试次数
        self.retry_interval = 5  # 重试间隔时间（秒）
        # 启动一个处理线程
        # threading.Thread(target=self._process_frames, daemon=True).start()

    def start_capture(self, task_id):
        if not self.is_running:
            # self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_FFMPEG, 1)
            # self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 初始化时设置
            self.is_running = True
            self.task_id = task_id

            fps = self.cap.get(cv2.CAP_PROP_FPS)
            print("视频流帧率：", fps)

            threading.Thread(target=self.video_loop, daemon=True).start()
            cur_time = datetime.now()
            task_dao.update_unfin_task_status(2, cur_time)
            #插入task信息
            new_task = FaceIdentityTask(
                status=1,
                task_id=task_id,
                create_time=cur_time
            )
            task_dao.save(new_task)
            threading.Thread(target=self.handle_identy_person_from_que, daemon=True).start()

    def stop_capture(self, task_id):
        self.is_running = False
        if self.cap:
            self.cap.release()
            task_dao.update_identy_task_status(2, datetime.now(), task_id)

    #检测人脸，提取正常角度人脸图片，并入MQ
    def _reconnect(self):
        """重新连接RTSP流，并增加重试次数限制"""
        if self.retry_count >= self.max_retry_attempts:
            print(f"Reached maximum retry attempts ({self.max_retry_attempts}), stopping capture.")
            self.is_running = False
            cur_time = datetime.now()
            task_dao.update_unfin_task_status(2, cur_time)
            return

        if self.cap:
            self.cap.release()

        print(f"Attempting to reconnect to RTSP stream (attempt {self.retry_count + 1}/{self.max_retry_attempts})...")
        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_FFMPEG, 1)

        if not self.cap.isOpened():
            self.retry_count += 1
            print(f"Reconnection failed. Retrying in {self.retry_interval} seconds...")
            time.sleep(self.retry_interval)
        else:
            self.retry_count = 0
            print("Reconnection successful.")

    def video_loop(self):
        last_process_time = time.time()
        while self.is_running:
            current_time = time.time()

            remaining = self.cap_period - (current_time - last_process_time)
            if remaining > 0:
                sleep_time = max(min(remaining, 0.5), 0.02)
                time.sleep(sleep_time)
                continue

            try:
                if cv2.__version__ >= '4.0.0':
                    self.cap.grab()

                ret, frame = self.cap.retrieve()
                # ret, frame = self.cap.read()
                img_str = capedImgUtil.frame_to_base64(frame)
                now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print(f"------{now_time}, frame:  {img_str}   ")
                if ret:
                    processed_frame, faces = self.video_processor.process_detect_frame(frame)


                    # print(f"------{now_time}, frame:  {img_str} ")

                    faces_img_base64str = capedImgUtil.process_extract_faces(processed_frame, faces)
                    self.face_img_str_to_mq(faces_img_base64str)
                    last_process_time = time.time()
                else:
                    time.sleep(1)
                    self._reconnect()

            except Exception as e:
                print(f"Frame processing error: {str(e)}")
                self._reconnect()

    # def video_loop(self):
    #     last_process_time = time.time()
    #     while self.is_running:
    #         current_time = time.time()
    #
    #         # 计算剩余等待时间（动态调整sleep时长）
    #         remaining = self.cap_period - (current_time - last_process_time)
    #
    #         if remaining > 0:
    #             # 动态sleep策略：在接近处理点时减少sleep时间
    #             sleep_time = max(min(remaining, 0.5), 0.02)  # 范围：20ms~500ms
    #             time.sleep(sleep_time)
    #             continue
    #
    #         # 清空缓冲区并读取最新帧
    #         try:
    #             if cv2.__version__ >= '4.0.0':
    #                 self.cap.grab()  # OpenCV 4+ 专用方法
    #
    #             # 1）拉取的流某一帧，2）检测是否有人，对侦测出的正常角度人像，3）base64后入MQ
    #             # 1）先尝试获取帧
    #             ret, frame = self.cap.retrieve()
    #
    #             if ret:
    #                 # 2）检测是否有人，侦测出的正常角度人像
    #                 processed_frame, faces = self.video_processor.process_detect_frame(frame)
    #                 # 3）正常角度人像提取base64后入MQ
    #                 faces_img_base64str = capedImgUtil.process_extract_faces(processed_frame, faces)
    #                 self.face_img_str_to_mq(faces_img_base64str)
    #                 last_process_time = time.time()
    #             else:
    #                 # 重试逻辑：等待1秒后尝试重新连接
    #                 time.sleep(1)
    #                 self._reconnect()
    #
    #         except Exception as e:
    #             print(f"Frame processing error: {str(e)}")
    #             self._reconnect()
    #
    # def _reconnect(self):
    #     if self.cap:
    #         self.cap.release()
    #     self.cap = cv2.VideoCapture(self.rtsp_url)
    #     self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 增大缓冲区
    #     self.cap.set(cv2.CAP_FFMPEG, 1)

    def face_img_str_to_mq(self, faces_img_base64str):
        if faces_img_base64str:
            for face_img in faces_img_base64str:
                self.frame_queue.put(face_img)

    #从MQ拉取数据
    def handle_identy_person_from_que(self):
        while self.is_running:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                res_user_info = self.video_processor.identify_person_1n(frame)
                self.handle_identy_res(res_user_info, frame)
            time.sleep(1)

    def handle_identy_res(self, res_user_info, frame):
        """
        处理解析结果，根据group_id和score进行不同操作
        :param frame:
        :param res_user_info:
        """
        # print(f"handle_identy_res res_user_info：{str(res_user_info)}")
        # error_code != 0 说明这张图片有问题，不做任何操作
        if res_user_info and res_user_info.get("error_code") != 0:
            return

        if not res_user_info or res_user_info is None:
            print("handle_identy_res 未找到用户信息, 进行新注册，并保存")
            usr_id = self.save_new_person_image_and_operate_db(frame)
            self.video_processor.reg_person_face(frame, SEARCH_GROUP_VISITOR, usr_id)
            return

        group_id = res_user_info.get("group_id")
        user_id = res_user_info.get("user_id")
        print(f"handle_identy_res group_id：{group_id},user_id：{user_id}")
        if group_id == SEARCH_GROUP_STAFF:
            return   # 返回用户信息
        elif group_id == SEARCH_GROUP_VISITOR:
            self.handle_update_visitor_cnt_and_face_img(user_id, group_id, frame)


    def handle_update_visitor_cnt_and_face_img(self, user_id, group_id, frame):
        """
        处理访客信息，操作数据库
        :param face_token: 面部识别token
        """
        user_base_info = visitor_base_info_dao.get_user_by_id(user_id)
        print(f"handle_update_visitor_cnt user：{str(user_base_info)}")
        if not user_base_info:
            self.save_image_and_operate_db(frame, user_id)
            return

        # task_user_agg_data = visitor_task_agg_dao.get_task_agg_data_by_task_user(user_id, self.task_id)
        # face_recg_cnt_cur_task = task_user_agg_data.face_recg_cnt_cur_task + 1
        # print(f"handle_identy_res 更新访客：{user_id}，次数：{face_recg_cnt_cur_task}")
        last_time=datetime.now()
        usr_img_path = capedImgUtil.build_visitor_img_save_path_with_ts(user_id, last_time)
        # new_face_visitor_task_agg_data = FaceVisitorTaskAggData(
        #     id = task_user_agg_data.id,
        #     task_id=self.task_id,
        #     user_id=user_id,
        #     face_recg_cnt_cur_task=face_recg_cnt_cur_task,
        #     face_last_identy_time=last_time
        # )
        # visitor_task_agg_dao.update(new_face_visitor_task_agg_data)
        new_visit_record = FaceIdentityRecord(
            task_id=self.task_id,
            user_id=user_id,
            group_id=SEARCH_GROUP_VISITOR,
            face_img_path=self.remove_leading_dot(usr_img_path),
            show_status=0,
            face_identy_time=last_time,
            enhance_status=0,
        )
        record_id = record_dao.save(new_visit_record)

        img = capedImgUtil.trans_img_base64_to_img(frame)
        capedImgUtil.save_image_to_path(img, user_id, last_time)
        try:
            # send enhance task
            send_enhance_task(record_id=record_id, user_id=user_id, task_id=self.task_id, user_image_relative_path=usr_img_path)
        except Exception as e:
            print(f"发送队列失败. record_id={record_id}, user_id={user_id},task_id={self.task_id}, user_image={usr_img_path}, e={e}")
            record_dao.enhance_error(record_id, f"发送识别队列失败. {e}")


    def save_new_person_image_and_operate_db(self, face_img):
        usr_id = self.generate_random_string(VISITOR_PREFIX)
        self.save_image_and_operate_db(face_img, usr_id)
        return usr_id

    def save_image_and_operate_db(self, face_img, usr_id):
        person_img_dir = self.save_image(face_img, usr_id)
        return self.save_usr_to_db(person_img_dir, usr_id)



    # ./ visitor_face\visitor_visitor_1741017251245
    def save_image(self, face_img, usr_id):
        """
                保存图片到本地目录，并操作数据库
                :param img: 图片数据
                :param face_token: 面部识别token
                """
        if (not usr_id):
            usr_id = self.generate_random_string(VISITOR_PREFIX)
        img_bytes = base64.b64decode(face_img)

        # 将字节数据转换为numpy数组
        img_np = np.frombuffer(img_bytes, dtype=np.uint8)

        # 使用OpenCV解码图像
        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

        person_dir = capedImgUtil.save_new_visitor_in_def_path(img, usr_id)
        return person_dir

    def remove_leading_dot(self, s):
        if s.startswith('.'):
            return s[1:]
        else:
            return s

    def save_usr_to_db(self, person_dir, usr_id):
        new_visit_record = FaceIdentityRecord(
            task_id=self.task_id,
            user_id=usr_id,
            group_id=SEARCH_GROUP_VISITOR,
            face_img_path=self.remove_leading_dot(person_dir),
            show_status=0,
            face_identy_time=datetime.now(),
            enhance_status=0
        )
        new_visit_base_info = FaceVisitorBaseInfo(
            user_id=usr_id,
            first_face_img_path=self.remove_leading_dot(person_dir),
            face_first_identy_time=datetime.now(),
            face_last_identy_time=datetime.now()
        )
        new_visit_task_agg_info = FaceVisitorTaskAggData(
            task_id=self.task_id,
            user_id=usr_id,
            face_recg_cnt_cur_task=1,
            face_first_identy_time=datetime.now(),
            face_last_identy_time=datetime.now()
        )
        record_dao.save(new_visit_record)
        visitor_base_info_dao.save(new_visit_base_info)
        visitor_task_agg_dao.save(new_visit_task_agg_info)
        return usr_id
    # def save_image_and_operate_db(self, face_img, usr_id):
    #     """
    #     保存图片到本地目录，并操作数据库
    #     :param img: 图片数据
    #     :param face_token: 面部识别token
    #     """
    #     if(not usr_id):
    #         usr_id = self.generate_random_string(VISITOR_PREFIX)
    #     img_bytes = base64.b64decode(face_img)
    #
    #     # 将字节数据转换为numpy数组
    #     img_np = np.frombuffer(img_bytes, dtype=np.uint8)
    #
    #     # 使用OpenCV解码图像
    #     img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    #
    #     person_dir = CapedImgUtil.save_new_visitor_in_dir(img, usr_id)
    #     new_visit_record = FaceIdentityRecord(
    #         task_id=self.task_id,
    #         user_id = usr_id,
    #         group_id= SEARCH_GROUP_VISITOR,
    #         face_img_path= person_dir,
    #         face_recg_cnt_cur_task= 1,
    #         face_first_identy_time=datetime.now(),
    #         face_last_identy_time=datetime.now()
    #     )
    #     record_dao.save(new_visit_record)
    #     return usr_id


    def generate_random_string(self, prefix_str):
        """
        生成随机字符串
        :param prefix_str: 前缀字符串
        :return: 随机字符串
        """
        # 获取当前时间戳
        timestamp = str(int(time.time()))
        # 生成1000以内的随机数
        random_num = RANDOM.randint(0, 999)
        # 拼接结果
        result = f"{prefix_str}{timestamp}{random_num}"
        return result



