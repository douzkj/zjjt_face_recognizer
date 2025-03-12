import json

import pika


from enhance_que import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD, RABBITMQ_VHOST, ENHANCE_TOPIC



def send_enhance_task(user_id, task_id, user_image_relative_path):
    # 建立与 RabbitMQ 服务器的连接
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=
                                                                   RABBITMQ_HOST,
                                                                   port=RABBITMQ_PORT,
                                                                   credentials=
                                                                   pika.PlainCredentials(username=RABBITMQ_USERNAME,
                                                                                         password=RABBITMQ_PASSWORD),
                                                                   virtual_host=RABBITMQ_VHOST
                                                                   )
                                         )
    try:
        task_obj = {
            "user_id": user_id,
            "task_id": task_id,
            "user_image": user_image_relative_path
        }
        message = json.dumps(task_obj)
        channel = connection.channel()
        channel.queue_declare(ENHANCE_TOPIC, durable=True)
        channel.basic_publish(body=message, exchange='', routing_key='zjjt.face_enhance')
        print(f'发送成功. message={message}')
    finally:
        connection.close()
