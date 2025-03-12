# rtsp_controller.py
import threading
import time
import uuid

import cv2
from flask import Flask

app = Flask(__name__)


class RTSPTask:
    def __init__(self, task_id, rtsp_url, cap_period=5):
        self.task_id = task_id
        self.rtsp_url = rtsp_url
        self.cap_period = cap_period
        self.is_running = False
        self.cap = None
        self.thread = None

    def start(self, frame_handler):
        self.is_running = True
        self.thread = threading.Thread(
            target=self._video_loop,
            args=(frame_handler,),
            daemon=True
        )
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def _video_loop(self, frame_handler):
        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

        last_process_time = time.time()
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(1)
                continue

            current_time = time.time()
            if current_time - last_process_time >= self.cap_period:
                last_process_time = current_time
                frame_handler(self.task_id, frame)

            time.sleep(0.02)


class RTSPManager:
    def __init__(self):
        self.tasks = {}
        self.frame_handlers = []

    def start_task(self, rtsp_url, cap_period):
        task_id = str(uuid.uuid4())
        task = RTSPTask(task_id, rtsp_url, cap_period)
        self.tasks[task_id] = task

        def handler(frame):
            for callback in self.frame_handlers:
                callback(task_id, frame)

        task.start(handler)
        return task_id

    def stop_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id].stop()
            del self.tasks[task_id]
            return True
        return False

    def register_frame_handler(self, handler):
        self.frame_handlers.append(handler)


# Flask API Endpoints
rtsp_manager = RTSPManager()


# @app.route('/cap/start', methods=['POST'])
# def start_capture():
#     data = request.json
#     task_id = rtsp_manager.start_task(
#         rtsp_url=data['rtsp_url'],
#         cap_period=data.get('cap_period', 5)
#     )
#     return jsonify({
#         "code": 0,
#         "msg": "任务已启动",
#         "task_id": task_id
#     })
#
#
# @app.route('/cap/stop/<task_id>', methods=['POST'])
# def stop_capture(task_id):
#     success = rtsp_manager.stop_task(task_id)
#     if success:
#         return jsonify({"code": 0, "msg": "任务已停止"})
#     return jsonify({"code": 404, "msg": "任务不存在"}), 404


# if __name__ == '__main__':
#     app.run(host='127.0.0.1', port=5001)