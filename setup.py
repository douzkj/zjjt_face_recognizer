import os

from face_recon_man.controller.face_recong_result_controller import face_recon_man_bp
from server.common.across_allow_filter import app
from server.img_proxy_server.visitor_images_proxy import img_proxy_bp
from stream_cap.controller.rtsp_stream_cap_controller import stream_cap_man_bp
from webrtc.webrtc_gateway import webrtc_gateway_bp

# setup(
#     name="stream-gateway",
#     version="0.1",
#     packages=[""],
#     install_requires=[
#         'aiohttp>=3.8.0',
#         'aiortc>=1.0',
#         'opencv-python-headless>=4.5.0',
#         'numpy>=1.21.0'
#     ],
#     entry_points={
#         'console_scripts': [
#             'stream-gateway=webrtc_gateway:main'
#         ]
#     }
# )

UI_PROXY_PORT = 28001

if __name__ == '__main__':
    app.register_blueprint(stream_cap_man_bp)
    app.register_blueprint(webrtc_gateway_bp)
    app.register_blueprint(img_proxy_bp)
    app.register_blueprint(face_recon_man_bp)
    PUB_PORT = os.getenv('PUB_PORT', 19090)

    app.run(host='0.0.0.0', port=PUB_PORT)
