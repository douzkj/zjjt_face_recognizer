import asyncio
import os
import threading
import time
import traceback
import uuid
from collections import defaultdict

import cv2
import numpy as np
from aiohttp import web
from aiortc import VideoStreamTrack, RTCPeerConnection, RTCSessionDescription
from av import VideoFrame
from flask import Blueprint, request, jsonify

# ====================== 全局配置 ======================
RTSP_TASKS = defaultdict(dict)  # 存储所有转码任务
TASK_TIMEOUT = 300  # 任务超时时间(秒)
PUB_PORT = os.getenv('PUB_PORT',
                     9090)
PUB_IP = os.getenv('PUB_IP',
                     '127.0.0.1')

webrtc_gateway_bp = Blueprint('web_rtc', __name__)

class FrameProvider:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.latest_frame = np.zeros((480, 640, 3), dtype=np.uint8)  # 初始黑帧
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        while self.running:
            cap = None
            try:
                cap = self._open_capture()
                if not cap.isOpened():
                    raise RuntimeError("无法打开视频流")

                while self.running:
                    ret, frame = cap.read()
                    if not ret:
                        print("视频帧读取失败，尝试重连...")
                        break

                    with self.lock:
                        self.latest_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            except Exception as e:
                print(f"RTSP连接异常: {str(e)}")
                traceback.print_exc()

            finally:
                if cap is not None:
                    cap.release()
                if self.running:  # 仅在运行状态下重连
                    time.sleep(2)  # 重连间隔增加至2秒

    def _open_capture(self):
        cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开RTSP流: {self.rtsp_url}")

        # 优化视频流参数
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
        return cap

    def get_frame(self):
        with self.lock:
            return self.latest_frame.copy()

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                print("警告: 视频采集线程未正常退出")

# ---------------------- 视频流轨道 ----------------------
class RTSPStreamTrack(VideoStreamTrack):
    def __init__(self, provider):
        super().__init__()
        self.provider = provider
        self._last_frame = None

    async def recv(self):
        try:
            pts, time_base = await self.next_timestamp()

            # 获取视频帧（最多等待500ms）
            frame = None
            for _ in range(50):
                if (frame := self.provider.get_frame()) is not None:
                    break
                await asyncio.sleep(0.01)
            else:
                raise RuntimeError("获取视频帧超时")

            video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            return video_frame
        except Exception as e:
            print(f"视频帧处理异常: {str(e)}")
            raise


# @webrtc_gateway_bp.route('/offer/<string:task_id>', methods=['POST'])
# async def offer(task_id):
#     print("-----------------offer")
#     response = make_response()
#     response.headers.add('Access-Control-Allow-Origin', '*')
#     response.headers.add('Access-Control-Allow-Methods', 'POST')
#     response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
#
#     """处理WebRTC协商请求"""
#     data = request.get_json()
#     task_id = data.get('task_id')
#     task = transcoder.get_task(task_id)
#
#     if not task or not task["active"]:
#         return jsonify({"error": "Invalid task"}, status=404), 200
#
#     try:
#         params = await request.json()
#         offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
#         pc = RTCPeerConnection()
#
#         # 添加视频轨道
#         track = RTSPStreamTrack(task["provider"])
#         pc.addTrack(track)
#
#         # 显式配置所有传输器方向（关键修复）
#         for transceiver in pc.getTransceivers():
#             if transceiver.kind == "video":
#                 transceiver.direction = "sendonly"  # 强制设置为仅发送
#                 transceiver._offerDirection = "sendonly"  # 内部方向同步
#             else:
#                 transceiver.stop()  # 禁用非视频传输器
#
#         # 设置远端描述
#         await pc.setRemoteDescription(offer)
#
#         # 创建Answer
#         answer = await pc.createAnswer()
#
#         # 修正SDP中的BUNDLE分组
#         def fix_bundle(sdp):
#             lines = sdp.split('\n')
#             bundle_lines = [i for i, line in enumerate(lines) if line.startswith('a=group:BUNDLE')]
#             video_mids = [i for i, line in enumerate(lines) if 'm=video' in line and 'a=mid:' in lines[i + 1]]
#
#             if bundle_lines and video_mids:
#                 video_mid = lines[video_mids[0] + 1].split(':')[1].strip()
#                 lines[bundle_lines[0]] = f'a=group:BUNDLE {video_mid}'
#             return '\n'.join(lines)
#
#         answer = await pc.createAnswer()
#         answer = RTCSessionDescription(
#             sdp=fix_bundle(answer.sdp),
#             type=answer.type
#         )
#
#         # 在后端添加调试输出
#         print("修正后的Answer SDP:\n", answer.sdp)
#
#         # 设置本地描述前验证方向
#         print("[DEBUG] 传输器状态:")
#         for i, t in enumerate(pc.getTransceivers()):
#             print(f"Transceiver {i}: {t.kind} | dir={t.direction} | offerDir={t._offerDirection}")
#
#         await pc.setLocalDescription(answer)
#
#         # 等待ICE候选收集（最多3秒）
#         for _ in range(30):
#             if pc.iceGatheringState == "complete":
#                 break
#             await asyncio.sleep(0.1)
#         else:
#             print("警告: ICE候选收集未在3秒内完成")
#
#         return jsonify({
#             "sdp": pc.localDescription.sdp,
#             "type": pc.localDescription.type
#         }), 200
#
#     except Exception as e:
#         traceback.print_exc()
#         if "pc" in locals():
#             await pc.close()
#         return jsonify(
#             {"error": f"信令处理失败: {str(e)}"}, status=500
#         ), 200

@webrtc_gateway_bp.route('/api/offer/<task_id>', methods=['POST'])
async def offer(task_id):
    """处理WebRTC协商请求"""
    print("Received offer request for task:", task_id)
    print("Request headers:", request.headers)
    print("Request data:", request.get_data(as_text=True))

    data = request.get_json()
    task = transcoder.get_task(task_id)

    if not task or not task["active"]:
        return jsonify({"error": "Invalid task"}), 404

    try:
        offer = RTCSessionDescription(sdp=data.get("sdp"), type=data.get("type"))
        pc = RTCPeerConnection()

        # 添加视频轨道
        track = RTSPStreamTrack(task["provider"])
        pc.addTrack(track)

        # 显式配置所有传输器方向（关键修复）
        for transceiver in pc.getTransceivers():
            if transceiver.kind == "video":
                transceiver.direction = "sendonly"  # 强制设置为仅发送
                transceiver._offerDirection = "sendonly"  # 内部方向同步
            else:
                transceiver.stop()  # 禁用非视频传输器

        # 设置远端描述
        await pc.setRemoteDescription(offer)

        # 创建Answer
        answer = await pc.createAnswer()

        # 修正SDP中的BUNDLE分组
        def fix_bundle(sdp):
            lines = sdp.split('\n')
            bundle_lines = [i for i, line in enumerate(lines) if line.startswith('a=group:BUNDLE')]
            video_mids = [i for i, line in enumerate(lines) if 'm=video' in line and 'a=mid:' in lines[i + 1]]

            if bundle_lines and video_mids:
                video_mid = lines[video_mids[0] + 1].split(':')[1].strip()
                lines[bundle_lines[0]] = f'a=group:BUNDLE {video_mid}'
            return '\n'.join(lines)

        answer = await pc.createAnswer()
        answer = RTCSessionDescription(
            sdp=fix_bundle(answer.sdp),
            type=answer.type
        )

        # 在后端添加调试输出
        print("修正后的Answer SDP:\n", answer.sdp)

        # 设置本地描述前验证方向
        print("[DEBUG] 传输器状态:")
        for i, t in enumerate(pc.getTransceivers()):
            print(f"Transceiver {i}: {t.kind} | dir={t.direction} | offerDir={t._offerDirection}")

        await pc.setLocalDescription(answer)

        # 等待ICE候选收集（最多3秒）
        for _ in range(30):
            if pc.iceGatheringState == "complete":
                break
            await asyncio.sleep(0.1)
        else:
            print("警告: ICE候选收集未在3秒内完成")

        return jsonify({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }), 200

    except Exception as e:
        traceback.print_exc()
        if "pc" in locals():
            await pc.close()
        return jsonify({"error": f"信令处理失败: {str(e)}"}), 500




###############################

# ====================== 转码任务管理类 ======================
class Transcoder:
    def __init__(self):
        self.tasks = {}
        self.lock = threading.Lock()

    def create_task(self, rtsp_url):
        task_id = str(uuid.uuid4())
        with self.lock:
            self.tasks[task_id] = {
                "provider": FrameProvider(rtsp_url),
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) ,
                "active": True,
                "rtsp_url": rtsp_url
            }
        return task_id

    def stop_task(self, task_id):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]["provider"].stop()
                self.tasks[task_id]["active"] = False
                return True
            return False

    def stop_all_task(self):
        with self.lock:
            for task_id in self.tasks:
                self.tasks[task_id]["provider"].stop()
                self.tasks[task_id]["active"] = False
                return True
            return False

    def get_task(self, task_id):
        with self.lock:
            return self.tasks.get(task_id)


transcoder = Transcoder()


def extract_after_third_slash(url):
    # 使用 split 方法按 '/' 分割字符串
    parts = url.split('/')

    # 检查是否有足够的斜杠
    if len(parts) > 3:
        # 将第4个部分及之后的部分重新组合
        result = '/'.join(parts[3:])
        return result
    else:
        return "URL中没有足够的斜杠"



# ====================== 接口处理 ======================
@webrtc_gateway_bp.route('/api/stream-manage-gw/start-pull-trans', methods=['POST'])
async def handle_start_pull():
    """启动转码任务接口"""
    data = request.get_json()
    stream_url = data.get("stream_url")

    print("------" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  + "handle_start_pull start:", extract_after_third_slash(stream_url))

    if not stream_url:
        return jsonify({"error": "Missing stream_url"}, status=400), 200

    try:
        # 创建转码任务
        task_id = transcoder.create_task(stream_url)
        pull_url = f"http://{request.host}/offer/{task_id}"

        print("------" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  + "handle_start_pull end, taskid:", task_id)

        return jsonify({
            "task_id": task_id,
            "pull_url": pull_url
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}, status=500), 200

@webrtc_gateway_bp.route('/api/stream-manage-gw/stop-pull-trans', methods=['POST'])
async def handle_stop_pull():
    """停止转码任务接口"""
    data = request.get_json()
    task_id = data.get("task_id")
    print("------" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  + "handle_stop_pull start, task_id:", task_id)

    if not task_id:
        return web.json_response({"error": "Missing task_id"}, status=400)

    if transcoder.stop_task(task_id):
        print("------" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  + "handle_start_pull end.")
        return jsonify({"status": "stopped"})
    else:
        return jsonify({"error": "Task not found"}, status=404), 200

