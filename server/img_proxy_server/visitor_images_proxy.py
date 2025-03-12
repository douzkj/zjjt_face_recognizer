import logging
import os

from dotenv import load_dotenv
from flask import send_from_directory, Response, Blueprint

img_proxy_bp = Blueprint('img_proxy', __name__)

# 初始化 Flask 应用
# app = Flask(__name__)
# CORS(app)  # 允许跨域访问
load_dotenv()  # 加载环境变量

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 从环境变量获取基础路径
BASE_DIR = os.getenv('VISITOR_DIR_BASE_DIR', '/data/douzkj/face_recognizer/server/FaceIdentyMan/')


@img_proxy_bp.route('/api/visitor-images/<path:filename>', methods=['GET'])
def serve_image(filename):
    """安全代理本地图片文件"""
    try:
        # 验证路径安全
        requested_path = os.path.join(BASE_DIR, filename)
        resolved_path = os.path.realpath(requested_path)
        print(f"-------------requested_path:{requested_path},  resolved_path:{resolved_path}")
        # 防止路径遍历攻击
        if not resolved_path.startswith(os.path.realpath(BASE_DIR)):
            logging.warning(f"非法路径访问尝试: {filename}")
            return Response("禁止访问", status=403)

        # 检查文件存在性
        if not os.path.isfile(resolved_path):
            logging.warning(f"文件不存在: {resolved_path}")
            return Response("文件未找到", status=404)

        # 发送文件
        directory = os.path.dirname(resolved_path)
        filename = os.path.basename(resolved_path)
        logging.info(f"成功访问文件: {resolved_path}")
        return send_from_directory(directory, filename)

    except Exception as e:
        logging.error(f"服务器错误: {str(e)}", exc_info=True)
        return Response("服务器内部错误", status=500)


