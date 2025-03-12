
import asyncio

import aio_pika

RABBITMQ_HOST = 'localhost'
RABBITMQ_PORT = 5672
RABBITMQ_USERNAME = "admin"
RABBITMQ_PASSWORD = "acd1be2a"
RABBITMQ_VHOST = "/vhost"
ENHANCE_TOPIC = "zjjt_face_enhance"

async def process_enhance_task(channel, message):
    try:
        print(f"Received: {message.body.decode('utf-8')}")
        await message.ack()
    except Exception as e:
        print(f"Error processing message: {e}")
async def get_connection():
    connection = await aio_pika.connect_robust(host=RABBITMQ_HOST,
                                               port=RABBITMQ_PORT,
                                               username=RABBITMQ_USERNAME,
                                               password=RABBITMQ_PASSWORD,
                                               virtual_host=RABBITMQ_VHOST
                                               )
    print("连接成功！")
    # 创建通道
    return connection



async def consuming(connection):
    # 创建连接
    channel = await connection.channel()
    print("连接成功！")
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
