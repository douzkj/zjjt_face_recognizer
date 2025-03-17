import time
from random import Random

from dao.base_dao import TaskDAO, DB_URL, RecordDAO, VisitorImgDetailDAO, VisitorBaseInfoDAO, \
    VisitorTaskAggDataDAO
from util.img_util import CapedImgUtil

test_rtsp_url="rtsp://rtspstream:WpPKtiupaLFDguY4KUlEe@zephyr.rtsp.stream/movie"

# os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;8192000"
task_dao = TaskDAO(DB_URL)
record_dao = RecordDAO(DB_URL)
visitor_detail_dao = VisitorImgDetailDAO(DB_URL)
visitor_base_info_dao = VisitorBaseInfoDAO(DB_URL)
visitor_task_agg_dao = VisitorTaskAggDataDAO(DB_URL)

VISITOR_PREFIX = "visitor_"

RANDOM = Random(int(time.time()))
capedImgUtil = CapedImgUtil()

# RTSP拉流处理流程框架类
#1）拉流取图片帧，2）检测图片人脸正脸，3）从图片中抽取正脸后，入MQ
class FaceRecongResultService:
    def __init__(self):
        self.cap = None

    def qry_recong_visitor_list(self):
        return visitor_task_agg_dao.qry_visitor_records_list();

    def qry_recong_enhance_images(self):
        return visitor_task_agg_dao.qry_visitor_enhance_images()


    def qry_task_detail_list(self):
        return visitor_task_agg_dao.qry_task_detail_list();

    def qry_visitor_task_show_info(self, task_id):
        return visitor_task_agg_dao.qry_visitor_task_show_info(task_id);

    def qry_task_recong_visitor_num(self, task_id):
        return visitor_task_agg_dao.qry_task_recong_visitor_num(task_id);

    def qry_visitor_history_img(self, user_id):
        return visitor_task_agg_dao.qry_visitor_history_img(user_id);

    def push_identy_task_img_2_screen(self, records_to_update):
         visitor_task_agg_dao.batch_update_identy_task_img_show_status(records_to_update);

    def get_cur_collect_task_id(self):
        return visitor_task_agg_dao.get_cur_collect_task_id();

    def qry_visitor_wall_screen(self):
        return visitor_task_agg_dao.qry_visitor_wall_screen();




