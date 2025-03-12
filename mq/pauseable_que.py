# import asyncio
#
# class PausableQueue:
#     def __init__(self):
#         self.queue = asyncio.Queue()
#         self.is_paused = False  # 暂停状态标志
#         self.resume_event = asyncio.Event()  # 恢复事件触发器
#         self.resume_event.set()  # 初始设置为可运行
#
#     async def consumer(self):
#         while True:
#             # 如果暂停，等待恢复信号
#             if self.is_paused:
#                 print("[Consumer] Paused...")
#                 await self.resume_event.wait()
#
#             # 正常获取数据
#             item = await self.queue.get()
#             print(f"[Consumer] Processing: {item}")
#             self.queue.task_done()
#
#     async def pause(self):
#         """暂停消费"""
#         self.is_paused = True
#         self.resume_event.clear()
#         print("[System] Queue paused")
#
#     async def resume(self):
#         """恢复消费"""
#         self.is_paused = False
#         self.resume_event.set()
#         print("[System] Queue resumed")