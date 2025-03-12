import json
import os
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from dao.face_db_enty import FaceIdentityTask, FaceIdentityRecord, FaceVisitorBaseInfo, FaceUserGroup, \
    FaceVisitorTaskAggData

DB_IP = os.getenv('MYSQL_IP', '127.0.0.1')
DB_PORT = os.getenv('MYSQL_PORT', '3306')
DB_USER = os.getenv('MYSQL_USER', 'root')
DB_PWD = os.getenv('MYSQL_PWD', '<PASSWORD>')
DB_NAME = os.getenv('MYSQL_DB_NAME', 'db_face_recong_app')
# DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PWD}@{DB_IP}/{DB_NAME}"
# DB_URL = "mysql+pymysql://root:123456@localhost/db_face_recong_app"
DB_URL = "mysql+pymysql://db_face_recong_app:6eTZXJdPCTy3w7kj@localhost:3306/db_face_recong_app"

# 基础数据库操作类
class BaseDAO:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    # 通用保存方法
    def save(self, entity):
        with self.Session() as session:
            session.add(entity)
            session.commit()
            return entity.id  #

    # 通用更新方法
    def update(self, entity):
        with self.Session() as session:
            merged_entity = session.merge(entity)
            session.commit()
            return merged_entity

    # 通用删除方法
    def delete(self, entity_class, entity_id):
        with self.Session() as session:
            entity = session.query(entity_class).get(entity_id)
            if entity:
                session.delete(entity)
                session.commit()
                return True
            return False

    # 通用查询方法
    def get_by_id(self, entity_class, entity_id):
        with self.Session() as session:
            return session.query(entity_class).get(entity_id)



# 具体业务操作类
class TaskDAO(BaseDAO):
    def get_tasks_by_status(self, status):
        with self.Session() as session:
            return session.query(FaceIdentityTask) \
                .filter(FaceIdentityTask.status == status) \
                .all()

    def get_recent_tasks(self, hours=24):
        with self.Session() as session:
            cutoff = datetime.now() - timedelta(hours=hours)
            return session.query(FaceIdentityTask) \
                .filter(FaceIdentityTask.create_time >= cutoff) \
                .order_by(FaceIdentityTask.create_time.desc()) \
                .all()

    def update_unfin_task_status(self, status, end_time):
        with self.Session() as session:
            sql = text("""
                update face_identity_task
                set status = :status , end_time = :end_time
                where status = 1
             """)
            session.execute(sql, {'status': status, 'end_time': end_time })
            session.commit()

    def update_identy_task_status(self, status, end_time, task_id):
        with self.Session() as session:
            sql = text("""
                update face_identity_task
                set status = :status , end_time = :end_time
                where task_id = :task_id
             """)
            session.execute(sql, {'status': status, 'end_time': end_time, 'task_id': task_id})
            session.commit()



class RecordDAO(BaseDAO):
    def get_records_by_user(self, user_id):
        with (self.Session() as session):
            return session.query(FaceIdentityRecord) \
                .filter(FaceIdentityRecord.user_id == user_id).first()
    def get_records_by_task_user(self, user_id, task_id):
        with self.Session() as session:
            return session.query(FaceIdentityRecord) \
                .filter(FaceIdentityRecord.user_id == user_id) \
                .filter(FaceIdentityRecord.task_id == task_id) \
                .first()

    def get_active_records(self):
        with self.Session() as session:
            return session.query(FaceIdentityRecord) \
                .filter(FaceIdentityRecord.show_status == 1) \
                .order_by(FaceIdentityRecord.face_last_identy_time.desc()) \
                .all()

    def enhance_success(self, user_id, task_id, enhance_img_path, remark=None):
        with self.Session() as session:
            sql = text("""
                update face_identity_record
                set enhance_status = :status , enhance_remark = :remark, enhance_img_path = :enhance_img_path
                where user_id = :user_id and task_id = :task_id
             """)
            session.execute(sql, {'status': 2, 'remark': "success" if remark is None else remark,
                                  "user_id": user_id, "task_id": task_id,
                                  "enhance_img_path": enhance_img_path
                                  })
            session.commit()

    def enhance_error(self, user_id, task_id, remark):
        with self.Session() as session:
            sql = text("""
                       update face_identity_record
                       set enhance_status = :status , enhance_remark = :remark
                       where user_id = :user_id and task_id = :task_id
                    """)
            session.execute(sql, {'status': 3, 'remark': "error" if remark is None else remark,
                                  "user_id": user_id,
                                  "task_id": task_id})
            session.commit()




class VisitorBaseInfoDAO(BaseDAO):
    def get_user_by_id(self, user_id):
        with self.Session() as session:
            return session.query(FaceVisitorBaseInfo) \
                .filter(FaceVisitorBaseInfo.user_id == user_id) \
                .first()

    def get_users_by_group(self, group_id):
        with self.Session() as session:
            return session.query(FaceVisitorBaseInfo) \
                .filter(FaceVisitorBaseInfo.group_id == group_id) \
                .all()

class VisitorTaskAggDataDAO(BaseDAO):
    def get_recong_usr_cnt_by_task_id(self, task_id):
        with self.Session() as session:
            return session.query(FaceVisitorTaskAggData) \
                .filter(FaceVisitorTaskAggData.task_id == task_id) \
                .count()

    def get_task_agg_data_by_task_user(self, user_id, task_id):
        with self.Session() as session:
            return session.query(FaceVisitorTaskAggData) \
                .filter(FaceVisitorTaskAggData.user_id == user_id) \
                .filter(FaceVisitorTaskAggData.task_id == task_id) \
                .first()

    def qry_visitor_enhance_images(self):
        with self.Session() as session:
            sql = text("""
                            SELECT 
                            user_id, 
                            task_id,
                            face_img_path as original_face_image,
                            enhance_status,
                            enhance_img_path as enhance_face_image,
                            enhance_remark,
                            face_identy_time as face_time
                            from face_identity_record
                            where enhance_status = 2
                            order by face_identy_time desc
                        """)
            result = session.execute(sql)
            return self.parse_sql_res_2_json(result)

    def qry_visitor_records_list(self):
        with self.Session() as session:
            sql = text("""
                SELECT t1.user_id, t1.visit_cnt, t1.first_visit_time, t1.last_visit_time, t2.first_face_img_path
                FROM (
                    SELECT user_id, COUNT(*) AS visit_cnt, MIN(face_identy_time) AS first_visit_time
                        , MAX(face_identy_time) AS last_visit_time
                    FROM face_identity_record
                    GROUP BY user_id
                ) t1
                    JOIN face_visitor_base_info t2 ON t1.user_id = t2.user_id
                ORDER BY t1.last_visit_time DESC;
            """)
            result = session.execute(sql)
            return self.parse_sql_res_2_json(result)

    def qry_task_detail_list(self):
        with self.Session() as session:
            sql = text("""
                 SELECT t1.create_time, t1.end_time, t1.status, t2.idt_cnt, t1.task_id
                FROM (
                    SELECT *
                    FROM face_identity_task
                    
                ) t1
                   left JOIN (
                        SELECT task_id, COUNT(DISTINCT user_id) AS idt_cnt
                        FROM face_identity_record
                        GROUP BY task_id
                    ) t2
                    ON t1.task_id = t2.task_id
                    ORDER BY t1.create_time DESC
              """)
            result = session.execute(sql)
            return self.parse_sql_res_2_json(result)

    def qry_visitor_task_show_info(self, task_id):
        with self.Session() as session:
            sql = text("""
                select  id, t1.user_id, face_img_path, show_status,visit_cnt
                from( 
                 SELECT id, user_id, face_img_path, show_status
                                FROM face_identity_record
                                WHERE task_id = :task_id
                        ORDER BY face_identy_time DESC, show_status DESC
                              )t1 inner join (  
                  SELECT  user_id, count(*) as visit_cnt
                                FROM face_identity_record
                                WHERE task_id = :task_id
                                group by user_id) t2 on t1.user_id=t2.user_id
            """)
            print(f"---------------{sql}")
            result = session.execute(sql, {'task_id': task_id})
            return self.parse_sql_res_2_json(result)

    def qry_task_recong_visitor_num(self, task_id):
        with self.Session() as session:
            sql = text("""
                SELECT count(distinct(user_id)) AS recong_cnt
                    FROM face_identity_record
                    where task_id = :task_id
            """)
            result = session.execute(sql, {'task_id': task_id})
            return self.parse_sql_res_2_json_with_check_array_len(result, True)

    def qry_visitor_history_img(self, user_id):
        with self.Session() as session:
            sql = text("""
                SELECT face_img_path, face_identy_time
                FROM face_identity_record
                WHERE user_id = :user_id
                ORDER BY face_identy_time DESC
            """)
            result = session.execute(sql, {'user_id': user_id})
            return self.parse_sql_res_2_json(result)

    def batch_update_identy_task_img_show_status(self, records_to_update):
        with self.Session() as session:
            for record in records_to_update:
                session.query(FaceIdentityRecord).filter_by(id=record.id).update({
                    'show_status': record.show_status,
                    'face_identy_time': datetime.now()  # 如果需要更新时间，可以在这里设置
                })
            session.commit()



    def get_cur_collect_task_id(self):
        with self.Session() as session:
            sql = text("""
                 select task_id from
                face_identity_task
                where status=1
                order by create_time desc limit 1
             """)
            result = session.execute(sql)
            return self.parse_sql_res_2_json_with_check_array_len(result, True)


    def qry_visitor_wall_screen(self):
        with self.Session() as session:
            sql = text("""
                select  id, t1.user_id, face_img_path, visit_cnt
                from( 
                 SELECT id, user_id, face_img_path 
                                FROM face_identity_record 
				where show_status=1
                        ORDER BY face_identy_time DESC 
                              )t1 inner join (  
                  SELECT  user_id, count(*) as visit_cnt
                                FROM face_identity_record
                                group by user_id) t2 on t1.user_id=t2.user_id
             """)
            result = session.execute(sql)
            return self.parse_sql_res_2_json_with_check_array_len(result, False)



    def parse_sql_res_2_json(self, result):
        return self.parse_sql_res_2_json_with_check_array_len(result, False)

    def parse_sql_res_2_json_with_check_array_len(self, result, check_len):
        if result is None:
            return None  # 如果输入结果为 None，直接返回 None

        try:
            # 获取列名
            columns = result.keys()

            # 获取所有行数据
            rows = result.all()

            # 如果 rows 是空数组，直接返回空对象的 JSON 格式
            if not rows:
                return json.dumps({}, ensure_ascii=False, indent=4)

            # 将查询结果转换为列表字典格式
            result_data = []
            for row in rows:
                row_data = {}
                for col, val in zip(columns, row):
                    # 处理时间类型，将其转换为字符串
                    if isinstance(val, datetime):
                        val = val.strftime("%Y-%m-%d %H:%M:%S")
                    # 如果值为 None，可以选择将其转换为字符串 "null" 或保留 None
                    row_data[col] = val if val is not None else None
                result_data.append(row_data)

            # 判断结果数据的行数
            if len(result_data) == 1 and check_len:
                # 如果只有一组值，返回单个键值对对象
                json_result = json.dumps(result_data[0], ensure_ascii=False, indent=4)
            else:
                # 如果有多组值，返回数组
                json_result = json.dumps(result_data, ensure_ascii=False, indent=4)
            return json_result

        except Exception as e:
            # 捕获异常并返回错误信息
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=4)

class VisitorImgDetailDAO(BaseDAO):
    def get_user_by_id(self, user_id):
        with self.Session() as session:
            return session.query(FaceVisitorBaseInfo) \
                .filter(FaceVisitorBaseInfo.user_id == user_id) \
                .first()

    def get_users_by_group(self, group_id):
        with self.Session() as session:
            return session.query(FaceVisitorBaseInfo) \
                .filter(FaceVisitorBaseInfo.group_id == group_id) \
                .all()


class GroupDAO(BaseDAO):
    def get_all_groups(self):
        with self.Session() as session:
            return session.query(FaceUserGroup).all()

    def get_group_by_name(self, group_name):
        with self.Session() as session:
            return session.query(FaceUserGroup) \
                .filter(FaceUserGroup.group_name == group_name) \
                .first()


