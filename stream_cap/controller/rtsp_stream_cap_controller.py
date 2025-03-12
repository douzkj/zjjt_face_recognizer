# app.py
import threading
import uuid

from flask import request, jsonify, Blueprint

from face_ai_api.face_recognition_service import FaceRecognitionService
from stream_cap.rtsp_stream_cap_action_template import RTSPStreamCapActionTmplate

stream_cap_man_bp = Blueprint('stream_cap', __name__)

test_rtsp_url="rtsp://rtspstream:WpPKtiupaLFDguY4KUlEe@zephyr.rtsp.stream/movie"
face_service = FaceRecognitionService()

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



@stream_cap_man_bp.route('/api/cap/start', methods=['POST'])
def start_capture():
    data = request.get_json()
    print(f'---------------start data:{data}')
    cap_period = data.get('cap_period', 5)
    rtsp_url = data.get('rtsp_url', test_rtsp_url)

    # 在启动新任务前，先停止所有现有任务
    with task_lock:
        # 遍历所有现有任务并停止它们
        for task_id, stream in list(active_tasks.items()):
            try:
                stream.stop_capture(task_id)
            except Exception as e:
                print(f"Error stopping task {task_id}: {e}")
            # 移除任务
            del active_tasks[task_id]

    task_id = str(uuid.uuid4())
    print('---------------start:' + task_id)

    processor = DefaultVideoProcessor()
    stream = RTSPStreamCapActionTmplate(processor, cap_period=cap_period, rtsp_url=rtsp_url)
    stream.start_capture(task_id)

    with task_lock:
        active_tasks[task_id] = stream

    res = jsonify({'task_id': task_id}), 200
    print('---------------end:' + task_id)
    return res

# def start_capture_async(cap_period, rtsp_url, task_id):
#     processor = DefaultVideoProcessor()
#     stream = RTSPStreamCapActionTmplate(processor, cap_period=cap_period, rtsp_url=rtsp_url)
#     stream.start_capture(task_id)
#
#     with task_lock:
#         active_tasks[task_id] = stream

@stream_cap_man_bp.route('/api/cap/stop/<string:task_id>', methods=['POST'])
def stop_capture(task_id):
    print('---------------stop_capture:' + task_id)
    with task_lock:
        stream = active_tasks.pop(task_id, None)

    if stream:
        stream.stop_capture(task_id)
        return jsonify({'status': 'stopped'}), 200
    return jsonify({'error': 'Invalid task ID'}), 404


# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)
    # root = tk.Tk()
    # processor = DefaultVideoProcessor()
    # stream = RTSPStream(processor, cap_period=5, rtsp_url=test_rtsp_url)
    # stream.start_capture()
    # root.mainloop()
