from sqlalchemy import Column, Integer, String, Text, DateTime

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# 任务表实体
class FaceIdentityTask(Base):
    __tablename__ = 'face_identity_task'
    id = Column(Integer, primary_key=True)
    task_id = Column(String(128))
    status = Column(Integer)
    create_time = Column(DateTime)
    end_time = Column(DateTime)


# 识别记录表实体
class FaceIdentityRecord(Base):
    __tablename__ = 'face_identity_record'
    id = Column(Integer, primary_key=True)
    task_id = Column(String)
    user_id = Column(String)
    group_id = Column(String)
    face_img_path = Column(String(512))
    show_status = Column(Integer)
    face_identy_time = Column(DateTime)
    # 默认0未处理，1:处理中，2增强成功，3增强失败
    enhance_status = Column(Integer)
    enhance_img_path = Column(String(512))
    enhance_remark = Column(Text)

class FaceVisitorTaskAggData(Base):
    __tablename__ = 'face_identity_task_agg_data'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    task_id = Column(String)
    face_recg_cnt_cur_task = Column(Integer)
    face_last_identy_time = Column(DateTime)
    face_first_identy_time = Column(DateTime)

# 人员基本信息表实体
class FaceVisitorBaseInfo(Base):
    __tablename__ = 'face_visitor_base_info'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    first_face_img_path = Column(String(512))
    face_last_identy_time = Column(DateTime)
    face_first_identy_time = Column(DateTime)


# 人员分组表实体
class FaceUserGroup(Base):
    __tablename__ = 'face_user_group'
    id = Column(Integer, primary_key=True)
    group_name = Column(String(255))
    group_desp = Column(Text)
