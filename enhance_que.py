
import asyncio
import json
import os
from pathlib import Path

import aio_pika
from dotenv import load_dotenv

load_dotenv()  # 加载环境变量

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', '127.0.0.1')
RABBITMQ_PORT = os.getenv('RABBITMQ_PORT', 5672)
RABBITMQ_USERNAME = os.getenv('RABBITMQ_USERNAME', "admin")
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', "acd1be2a")
RABBITMQ_VHOST = os.getenv('RABBITMQ_VHOST', "/")
ENHANCE_TOPIC = os.getenv('ENHANCE_TOPIC', "zjjt_face_enhance")

def get_face_enhance_path(face_image_path):
    return os.path.splitext(face_image_path)[0]


def remove_leading_dot(s):
    if s.startswith('.'):
        return s[1:]
    else:
        return s

def do_codeformer_enhance(record_id, user_id, task_id, user_image):
    from util.codeformer_enhancer import enhance
    from stream_cap.rtsp_stream_cap_action_template import record_dao
    user_full_image = os.path.abspath(user_image)
    enhance_out_img_path = get_face_enhance_path(user_full_image)
    enhance_usr_img_path = remove_leading_dot(get_face_enhance_path(user_image))
    enhance_usr_img_path = os.path.join(enhance_usr_img_path, "final_results", os.path.basename(user_image))
    # 由于codeformer默认后缀为png 修改为png
    enhance_usr_img_path = Path(enhance_usr_img_path).with_suffix(".png")
    try:
        # 进行人脸增强
        ret, std = enhance(input_path=user_full_image, output_path=enhance_out_img_path)
        if ret is True:
            record_dao.enhance_success(record_id, enhance_usr_img_path, std)
        else:
            record_dao.enhance_error(record_id, std)
    except Exception as e:
        print(f"人脸增强异常. img={user_image}, enhance_usr_img_path={enhance_usr_img_path}, e={e}")
        record_dao.enhance_error(record_id, f"{e}")


async def process_enhance_task(channel, message):
    try:
        print(f"Received: {message.body.decode('utf-8')}")
        task_obj = json.loads(message.body.decode('utf-8'))
        do_codeformer_enhance(record_id=task_obj.get('record_id'),
                              user_id=task_obj.get("user_id"),
                              task_id=task_obj.get("task_id"),
                              user_image=task_obj.get("user_image"))
        await message.ack()
    except Exception as e:
        print(f"Error processing message: {e}")


async def get_connection():
    connection = await aio_pika.connect_robust(host=RABBITMQ_HOST,
                                               port=int(RABBITMQ_PORT),
                                               login=RABBITMQ_USERNAME,
                                               password=RABBITMQ_PASSWORD,
                                               virtualhost=RABBITMQ_VHOST
                                               )
    print("连接成功！")
    # 创建通道
    return connection



async def consuming(connection):
    # 创建连接
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=16)  # 设置预取数量为1，确保一次只处理一个消息
    queue = await channel.declare_queue(ENHANCE_TOPIC, durable=True)
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            await process_enhance_task(channel, message)


async def main():
    conn = await get_connection()
    try:
        await consuming(conn)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
