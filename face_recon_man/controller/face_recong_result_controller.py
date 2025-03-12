# app.py

import threading

from flask import jsonify, Blueprint, request

from dao.face_db_enty import FaceIdentityRecord
from face_ai_api.face_recognition_service import FaceRecognitionService
from face_recon_man.service.face_recong_result_service import FaceRecongResultService

test_rtsp_url="rtsp://rtspstream:WpPKtiupaLFDguY4KUlEe@zephyr.rtsp.stream/movie"
face_service = FaceRecognitionService()
face_recon_man_service = FaceRecongResultService()

face_recon_man_bp = Blueprint('face_recong_result', __name__)


class DefaultVideoProcessor:
    def process_detect_frame(self, frame):
        return face_service.detect_faces(frame)
        # face_service.process_extract_faces(faces)

    # def process_extract_faces(self, faces):
    #     return face_service.process_extract_faces(faces)

    def identify_person_1n(self, face_img):
        return face_service.identify_person_1n(face_img)

    def reg_person_face(self, face_img_base64_str, group_id, user_id):
        return face_service.reg_person_face(face_img_base64_str, group_id, user_id)


# 线程安全的任务存储
active_tasks = {}
task_lock = threading.Lock()



@face_recon_man_bp.route('/api/face-recong-man/visitor-list', methods=['GET'])
def qry_visitor_list():
    result = face_recon_man_service.qry_recong_visitor_list()
    print(f"---------------{result}")
    return {'data': result}, 200

@face_recon_man_bp.route('/api/face-recong-man/task-detail-list', methods=['GET'])
def qry_task_detail_list():
    result = face_recon_man_service.qry_task_detail_list()
    return {'data': result}, 200

@face_recon_man_bp.route('/api/face-recong-man/visitor-list-by-taskid', methods=['GET'])
def qry_visitor_list_by_taskid():
    result = face_recon_man_service.qry_task_detail_list()
    return {'data': result}, 200


@face_recon_man_bp.route('/api/face-recong-man/qry_visitor_task_show_info/<string:task_id>', methods=['GET'])
def qry_visitor_task_show_info(task_id):
    result = face_recon_man_service.qry_visitor_task_show_info(task_id)
    print(f"-----------qry_visitor_task_show_info----:{result}")
    return {'data': result}, 200

@face_recon_man_bp.route('/api/face-recong-man/qry_task_recong_visitor_num/<string:task_id>', methods=['GET'])
def qry_task_recong_visitor_num(task_id):
    result = face_recon_man_service.qry_task_recong_visitor_num(task_id)
    return result, 200

@face_recon_man_bp.route('/api/face-recong-man/qry_visitor_history_img/<string:user_id>', methods=['GET'])
def qry_visitor_history_img(user_id):
    result = face_recon_man_service.qry_visitor_history_img(user_id)
    return {'data': result}, 200


@face_recon_man_bp.route('/api/face-recong-man/push_identy_task_img_2_screen', methods=['POST'])
def push_identy_task_img_2_screen():
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({'error': 'Invalid data format'}), 400

        # 解析数据并构造FaceIdentityRecord对象数组
    records_to_update = []
    for item in data:
        if 'id' not in item or 'show_status' not in item:
            return jsonify({'error': 'Missing required fields in data'}), 400

        record = FaceIdentityRecord(
            id=item['id'],
            show_status=item['show_status']
        )
        records_to_update.append(record)
    face_recon_man_service.push_identy_task_img_2_screen(records_to_update)
    return {'msg': "succ"}, 200



@face_recon_man_bp.route('/api/face-recong-man/get_cur_collect_task_id', methods=['GET'])
def get_cur_collect_task_id():
    result = face_recon_man_service.get_cur_collect_task_id()
    # print(f"--------------xxx-res: {result}")
    # print(type(result))
    # if result == "{}":
    #    return {"task_id": null_result()}
    return result, 200

@face_recon_man_bp.route('/api/face-recong-man/visitor-wall-screen', methods=['GET'])
def visitor_wall_screen():
    result = face_recon_man_service.qry_visitor_wall_screen()
    # print(f"--------------xxx-res: {result}")
    # print(type(result))
    # if result == "{}":
    #    return {"task_id": null_result()}
    return result, 200



    # root = tk.Tk()
    # processor = DefaultVideoProcessor()
    # stream = RTSPStream(processor, cap_period=5, rtsp_url=test_rtsp_url)
    # stream.start_capture()
    # root.mainloop()
