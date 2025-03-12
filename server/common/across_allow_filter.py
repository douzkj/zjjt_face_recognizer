from flask import Flask, jsonify, request

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 跨域统一Filter
@app.after_request
def after_request(response):
    # 设置允许的域
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    # 设置允许的请求方法
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    # 设置允许的请求头
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    # 设置允许凭据（如Cookie）
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response