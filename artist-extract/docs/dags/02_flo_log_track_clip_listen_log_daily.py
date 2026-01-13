from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import boto3
import time 
import pendulum
from airflow.models import Variable
import base64
from botocore.exceptions import ClientError 

from airflow.operators.dummy import DummyOperator ##
from util.slack_alert import SlackAlert ##
from util.redshift_util import RedshiftUtils
from airflow.sensors.external_task_sensor import ExternalTaskSensor
from airflow.utils.task_group import TaskGroup ## task group package
from airflow.decorators import task
import sys

###################################################################################
##     수정일   /   수정자    /  수정내용 
## 2023.03.28 / Jiny / Task_10 flo_dwh_m_audio_episode_listen_stat_daily 추가
## 2023.04.18 / Jiny / Task_12 flo_dwh_m_audio_program_retention_daily 추가
## 2023.05.14 / Jiny / Task_13 flo_dwh_m_audio_program_listen_stat_daily 추가
## 2023.08.07 / Jiny / Task_14 flo_dwh_m_audio_cover_retention_daily 추가
## 2023.08.17 / Shen / Task_15 flo_dwh_m_cover_listen_stat_daily Task_16 flo_dwh_m_clip_cover_listen_stat_daily 추가
## 2023.12.19 / Blaine / retries 추가
## 2024.07.22 / Brett / RedshiftUtils.execute_sql, RedshiftUtils.ds_add 함수 redshift_util class 에서 호출하도록 변경, skipped alert 추가, get_secret_value 제거,  주석 추가
## 2024.08.26 / Brett / 날짜 관련 로직 ->메서드 내부호출로 변경, (ds, tomorrow_ds ) -> (**kwargs)로 변경, call_sp.replace() -> 메서드 내부호출로 변경, @task decorator 반영
## 2025.02.12 / Brett / msp alert 발생용 failure callback 함수 추가 : [alert.slack_fail_alert, alert.msp_fail_alert_webhook]
## 2025.05.30 / Brett / dependency_dag_1 timeout 7200으로 1시간 추가
## 2025.07.07 / Brett / kwargs['ds'] -> kwargs['data_interval_end'] 변경
###################################################################################

########################################## Define Default args ##########################################
#########################################################################################################
## 기본 Dag 매개변수등 기타 기본 설정값 부분 (가급적 건드리지 않는 부분)                                              ##
## 신규 Dag 작성시 start_date 부분은 수정 필요                                                                ##
#########################################################################################################
# dag_id 저장
dag_id = sys._getframe().f_code.co_filename.split('.')[0].split('/')[-1]
# slack Alert Class 호출
alert = SlackAlert('#floda-airflow') ##
# RedshiftUtils Class 호출
executeSql = RedshiftUtils(dag_id)

# 로컬 타임존 생성
local_tz = pendulum.timezone("Asia/Seoul")
    
DEFAULT_ARGS = {
    'owner': 'DataUnit',
    'depends_on_past': False,
    'start_date': datetime(2025,3,27, tzinfo=local_tz),
    'email': ['g-data@dreamus.io'],
    'email_on_failure': False,
    'email_on_retry': False, 
    'on_failure_callback' : [alert.slack_fail_alert, alert.msp_fail_alert_webhook],
    'on_success_callback' : alert.slack_skipped_alert, ## 상태값은 success 인데 내무적으로 success가 아닌 skipped등 다른 상태값일때 알림
    'retries' : 2,
    'retry_delay' : timedelta(minutes=1)
}
########################################## Define Default args ##########################################

########################################## Define python_callable #######################################
#########################################################################################################
## sp 호출을 위한 python callable 함수 정의 부분                                                             ##
## sp 호출시 설정할 변수 설정 및 call sql 정의, RedshiftUtils.execute_sql 호출                                 ##
#########################################################################################################

@task
def flo_log_clip_listen_daily(**kwargs):
    call_sp = """
    call flo_log.sp_clip_listen_daily_history_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_log_track_listen_daily(**kwargs):
    call_sp = """
    call flo_log.sp_track_listen_daily_history_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_log_audio_track_listen_daily(**kwargs):
    call_sp = """
    call flo_log.sp_audio_track_listen_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_audio_clip_track_listen_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_audio_clip_track_listen_stat_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_audio_listen_stat_hourly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_audio_listen_stat_hourly ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_audio_episode_listen_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_audio_episode_listen_stat_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_audio_program_retention_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_audio_program_retention_daily_upload ($sdate$ );
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_audio_program_listen_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_audio_program_listen_stat_daily_upload ($sdate$ );
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_member_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_member_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_playchnl_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_playchnl_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_auto_issu_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_auto_issu_monthly ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)
    
@task
def flo_dwh_m_member_flondata_issue_new_stat_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_flondata_issue_new_stat_monthly ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_audio_cover_retention_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_audio_cover_retention_daily_upload ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_cover_listen_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_cover_listen_stat_daily ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_clip_cover_listen_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_clip_cover_listen_stat_daily ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)
########################################## Define python_callable #######################################

########################################## call Dags #######################################################
############################################################################################################
## 실제 Dag 호출                                                                                             ##
## Define python_callable 부분에서 정의된 def를 실제 task로 지정하고 호출                                           ##
############################################################################################################
with DAG(
    dag_id='02_flo_log_track_clip_listen_log_daily',
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=5),
    schedule_interval='15 6 * * *',
    tags=['track listen', 'clip listen', 'audio', 'daily']
) as dag:

    # m_track_listen 에서 flo_poc.tb_track, flo_mcp.tnmm_track 을 바라봐 dependency 추가
    dependency_dag_1 = ExternalTaskSensor(
        task_id='wait_for_DAG01_end',
        external_dag_id='01_flo_poc_mcp_daily', # dependency 설정할 DAG ID
        external_task_id='send_alert', # dependency 설정할 TASK ID 미설정시 None으로 설정되어 선행 체크 하지 않으므로 꼭 설정 해줘야 함
        execution_date_fn=lambda x: x - timedelta(minutes=45), #  후행과 선행이 동일한 시간에 scheduling 된 경우 lambda x: x 사용. excution_delta or excution_data_fn 둘 중 하나의 파라미터만 입력해야 함. 선행 DAG의 스케줄 시간이 다른 경우 timedelta() 함수로 시간을 빼거나 더해줘야 함 ex) lambda x: x - timedelta(hours=3)
        mode='reschedule',             # 미설정시 default : poke (Sensor의 전체 실행 시간동안 worker 슬롯을 점유하며, poke 사이에는 sleep 상태로 존재) reschedule (조건을 만족하지 않았을 때 Sensor는 worker 슬롯을 놓아주고, 다음 번 확인을 위해 reschedule )
        timeout=7200,
    )

    task_1 = flo_log_clip_listen_daily()
    task_2 = flo_log_track_listen_daily()
    task_3 = flo_log_audio_track_listen_daily()
    task_4 = flo_dwh_m_audio_clip_track_listen_stat_daily()
    task_5 = flo_dwh_m_audio_listen_stat_hourly()
    task_6 = flo_dwh_m_track_listen_daily()
    task_7 = flo_dwh_m_track_listen_member_daily()
    task_8 = flo_dwh_m_track_listen_playchnl_daily()
    task_9 = flo_dwh_m_member_auto_issu_monthly()
    task_10 = flo_dwh_m_audio_episode_listen_stat_daily()
    task_11 = flo_dwh_m_member_flondata_issue_new_stat_monthly()
    task_12 = flo_dwh_m_audio_program_retention_daily()
    task_13 = flo_dwh_m_audio_program_listen_stat_daily()
    task_14 = flo_dwh_m_audio_cover_retention_daily()
    task_15 = flo_dwh_m_cover_listen_stat_daily()
    task_16 = flo_dwh_m_clip_cover_listen_stat_daily()
    
    send_alert = DummyOperator( ##
        task_id='send_alert', dag=dag,
        on_success_callback = alert.slack_success_alert
    )
    
    dependency_dag_1 >> task_1 >> task_2 >> task_3 >> task_4 >> task_5 >> task_10 >> task_12 >> task_13 >> task_14 >> task_6 >> task_7 >> task_8 >> [task_9, task_11] 
    dependency_dag_1 >> task_4 >> task_15 >> task_16 
    [task_1, task_2, task_3, task_4, task_5, task_6 , task_7, task_8, task_9, task_10] >> send_alert
    [task_11, task_12, task_13, task_14, task_15, task_16] >> send_alert
########################################## call Dags #######################################################
