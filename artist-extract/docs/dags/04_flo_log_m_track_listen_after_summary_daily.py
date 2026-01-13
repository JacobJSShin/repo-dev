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
## 2023.01.16 / Shen / Task_24 flo_dwh_m_alog_home_cura_daily 작업 제거 (DAG03으로 이동)
## 2023.02.01 / Shen / Task_26 m_member_login_summary_daily, Task_27 m_member_login_summary_weekly 추가
## 2023.02.08 / Shen / Task_28 flo_dwh_m_pass_activity_stat_monthly 추가
## 2023.02.15 / Shen / Task_29 flo_dwh_m_member_audio_first_listen_daily 추가
## 2023.08.11 / Gideon / Task_30 flo_dwh_m_track_listen_million_stat 추가
## 2023.09.13 / Jiny / Task_20 flo_dwh_m_flo_active_sum_daily  >> flo_dwh_m_flo_active_stat_daily_d로 변경 
## 2023.12.19 / Blaine / retries 추가
## 2024.02.27 / Tina / Task_31 flo_dwh_m_flo_contents_use_stat 추가
## 2024.05.09 / Shen / Task_32 flo_dwh_m_member_biz_partner_action_listen_stat_daily 추가
## 2024.05.24 / Shen / Task_32 flo_dwh_m_member_biz_partner_action_listen_stat_daily 제거
## 2024.05.24 / Shen / Task_32 flo_dwh.sp_m_biz_partner_member_action_cnt_daily, Task_33 flo_dwh.sp_m_biz_partner_member_track_listen_stat_daily 추가
## 2024.06.11 / Shen / Task_34 flo_dwh.sp_m_choigorae_vip_member_listen_pass_stat_daily 추가
## 2024.07.22 / Brett / Dag01, Dag02,Dag03-1 선행 추가, ds_add 함수 redshift_util class 에서 호출하도록 변경, skipped alert 추가, get_secret_value 제거, 주석 추가
## 2024.08.06 / Gideon / Task_35 flo_dwh.sp_m_playlist_member_retention_weekly 추가
## 2024.08.26 / Brett / 날짜 관련 로직 ->메서드 내부호출로 변경, (ds, tomorrow_ds ) -> (**kwargs)로 변경, call_sp.replace() -> 메서드 내부호출로 변경, @task decorator 반영
## 2025.01.13 / Brett / task_36~task_39 flo_dwh.sp_m_flo_listen_1min_stat_daily_upload, flo_dwh.sp_m_flo_listen_1min_stat_weekly_upload, flo_dwh.sp_m_flo_listen_1min_stat_monthly_upload, flo_dwh.sp_m_playlist_member_retention_monthly_upload 추가
## 2025.02.12 / Brett / msp alert 발생용 failure callback 함수 추가 : [alert.slack_fail_alert, alert.msp_fail_alert_webhook]
## 2025.04.10 / Brett / task 40~ 43 추가 flo_dwh.sp_m_playlist_result_indicator_daily_d, flo_dwh.sp_m_playlist_result_indicator_weekly_d, flo_dwh.sp_m_playlist_result_indicator_monthly_d, flo_dwh.sp_m_playlist_result_indicator_yearly_d
## 2025.05.28 / Gideon / SuperSet Index Dashboard 해외 MG권리사 일간 1분이상 청취현황 테이블(m_indexboard_mg_listen_monthly, m_indexboard_mg_listen_daily) 적재 SP 추가 (flo_dwh.sp_m_indexboard_mg_listen_daily)
## 2025.07.07 / Brett / kwargs['ds'] -> kwargs['data_interval_end'] 변경
## 2025.10.23 / Brett / ExternalTaskSensor 03_01 DAG 스케줄링 시간 조정 
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

## 로컬 타임존 생성
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
## sp 호출시 설정할 변수 설정 및 call sql 정의, execute_sql 호출                                               ##
#########################################################################################################
@task
def flo_dwh_m_flo_listen_stat_novod_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_listen_stat_novod_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_theme_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_theme_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_theme_dtl_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_theme_dtl_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_playlist_dtl_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_playlist_dtl_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_chnl_play_type_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_chnl_play_type_stat_daily ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_flo_listen_stat_novod_weekly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_listen_stat_novod_weekly_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_theme_weekly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_theme_weekly_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_theme_dtl_weekly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_theme_dtl_weekly_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_playlist_dtl_weekly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_playlist_dtl_weekly_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)


@task
def flo_dwh_m_flo_listen_stat_novod_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_listen_stat_novod_monthly_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_theme_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_theme_monthly_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_theme_dtl_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_theme_dtl_monthly_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_playlist_dtl_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_playlist_dtl_monthly_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_theme_hr_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_theme_hr_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_flo_listen_stat_novod_hr_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_listen_stat_novod_hr_daily_upload ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_login_summary_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_login_summary_monthly ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_login_summary_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_login_summary_monthly ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_rank_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_rank_daily_upload ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_rank_weekly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_rank_weekly_upload ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_rank_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_rank_monthly_upload ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_flo_active_stat_daily_d(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_active_stat_daily_d ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_program_list_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_program_list_daily ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_episode_list_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_episode_list_daily ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_label_listen_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_label_listen_daily ($sdate$, $edate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_login_summary_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_login_summary_daily ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_login_summary_weekly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_login_summary_weekly ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_track_listen_stat_svc_genre(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_stat_svc_genre_upload ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_pass_activity_stat_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_pass_activity_stat_monthly ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_audio_first_listen_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_audio_first_listen_daily ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)
    
@task
def flo_dwh_m_track_listen_million_stat(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_track_listen_million_stat_reload ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_flo_active_stat_daily_d(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_active_stat_daily_d ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_flo_contents_use_stat(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_contents_use_stat ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)    

@task
def flo_dwh_m_biz_partner_member_action_cnt_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_biz_partner_member_action_cnt_daily ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_biz_partner_member_track_listen_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_biz_partner_member_track_listen_stat_daily ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_choigorae_vip_member_listen_pass_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_choigorae_vip_member_listen_pass_stat_daily ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_playlist_member_retention_weekly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_playlist_member_retention_weekly ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_flo_listen_1min_stat_daily_upload(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_listen_1min_stat_daily_upload ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_flo_listen_1min_stat_weekly_upload(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_listen_1min_stat_weekly_upload ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_flo_listen_1min_stat_monthly_upload(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_listen_1min_stat_monthly_upload ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_playlist_member_retention_monthly_upload(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_playlist_member_retention_monthly_upload ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_playlist_result_indicator_daily_d(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_playlist_result_indicator_daily_d ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_playlist_result_indicator_weekly_d(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_playlist_result_indicator_weekly_d ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_playlist_result_indicator_monthly_d(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_playlist_result_indicator_monthly_d ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_playlist_result_indicator_yearly_d(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_playlist_result_indicator_yearly_d ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_indexboard_mg_listen_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_indexboard_mg_listen_daily ($sdate$);
    """ 
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)
    
########################################## Define python_callable #######################################

########################################## call Dags #######################################################
############################################################################################################
## 실제 Dag 호출                                                                                             ##
## Define python_callable 부분에서 정의된 def를 실제 task로 지정하고 호출                                           ##
############################################################################################################
with DAG(
    dag_id='04_flo_log_m_track_listen_after_summary_daily',
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=5),
    schedule_interval='10 8 * * *',
    tags=['track listen', 'playlist', 'theme','flo_dwh', 'daily', 'weekly', 'monthly']
) as dag:

    # TaskGroup 설정 (여러 dependency를 TaskGroup 하나로 묶어 가독성 향상)
    with TaskGroup("taskgroup_1", tooltip="task group #1", dag=dag) as section_1:
        dependency_dag_1 = ExternalTaskSensor(
            task_id='wait_for_DAG01_end',
            external_dag_id='01_flo_poc_mcp_daily', # dependency 설정할 DAG ID
            external_task_id='send_alert', # dependency 설정할 TASK ID 미설정시 None으로 설정되어 선행 체크 하지 않으므로 꼭 설정 해줘야 함
            execution_date_fn=lambda x: x - timedelta(minutes=160), #  후행과 선행이 동일한 시간에 scheduling 된 경우 lambda x: x 사용. excution_delta or excution_data_fn 둘 중 하나의 파라미터만 입력해야 함. 선행 DAG의 스케줄 시간이 다른 경우 timedelta() 함수로 시간을 빼거나 더해줘야 함 ex) lambda x: x - timedelta(hours=3)
            mode='reschedule',             # 미설정시 default : poke (Sensor의 전체 실행 시간동안 worker 슬롯을 점유하며, poke 사이에는 sleep 상태로 존재) reschedule (조건을 만족하지 않았을 때 Sensor는 worker 슬롯을 놓아주고, 다음 번 확인을 위해 reschedule )
            timeout=7200,
        )
        dependency_dag_2 = ExternalTaskSensor(
            task_id='wait_for_DAG02_end',
            external_dag_id='02_flo_log_track_clip_listen_log_daily', # dependency 설정할 DAG ID
            external_task_id='send_alert', # dependency 설정할 TASK ID 미설정시 None으로 설정되어 선행 체크 하지 않으므로 꼭 설정 해줘야 함
            execution_date_fn=lambda x: x - timedelta(minutes=115), #  후행과 선행이 동일한 시간에 scheduling 된 경우 lambda x: x 사용. excution_delta or excution_data_fn 둘 중 하나의 파라미터만 입력해야 함. 선행 DAG의 스케줄 시간이 다른 경우 timedelta() 함수로 시간을 빼거나 더해줘야 함 ex) lambda x: x - timedelta(hours=3)
            mode='reschedule',             # 미설정시 default : poke (Sensor의 전체 실행 시간동안 worker 슬롯을 점유하며, poke 사이에는 sleep 상태로 존재) reschedule (조건을 만족하지 않았을 때 Sensor는 worker 슬롯을 놓아주고, 다음 번 확인을 위해 reschedule )
            timeout=7200,
        )
        dependency_dag_3 = ExternalTaskSensor(
            task_id='wait_for_DAG03_01_end',
            external_dag_id='03_01_flo_action_log_daily', # dependency 설정할 DAG ID
            external_task_id='send_alert', # dependency 설정할 TASK ID 미설정시 None으로 설정되어 선행 체크 하지 않으므로 꼭 설정 해줘야 함
            execution_date_fn=lambda x: x - timedelta(minutes=300), #  후행과 선행이 동일한 시간에 scheduling 된 경우 lambda x: x 사용. excution_delta or excution_data_fn 둘 중 하나의 파라미터만 입력해야 함. 선행 DAG의 스케줄 시간이 다른 경우 timedelta() 함수로 시간을 빼거나 더해줘야 함 ex) lambda x: x - timedelta(hours=3)
            mode='reschedule',             # 미설정시 default : poke (Sensor의 전체 실행 시간동안 worker 슬롯을 점유하며, poke 사이에는 sleep 상태로 존재) reschedule (조건을 만족하지 않았을 때 Sensor는 worker 슬롯을 놓아주고, 다음 번 확인을 위해 reschedule )
            timeout=7200,
        )

    task_1 = flo_dwh_m_flo_listen_stat_novod_daily()
    task_2 = flo_dwh_m_track_listen_stat_theme_daily()
    task_3 = flo_dwh_m_track_listen_stat_theme_dtl_daily()
    task_4 = flo_dwh_m_track_listen_stat_playlist_dtl_daily()
    task_5 = flo_dwh_m_flo_listen_stat_novod_weekly()
    task_6 = flo_dwh_m_track_listen_stat_theme_weekly()
    task_7 = flo_dwh_m_track_listen_stat_theme_dtl_weekly()
    task_8 = flo_dwh_m_track_listen_stat_playlist_dtl_weekly()
    task_9 = flo_dwh_m_flo_listen_stat_novod_monthly()
    task_10 = flo_dwh_m_track_listen_stat_theme_monthly()
    task_11 = flo_dwh_m_track_listen_stat_theme_dtl_monthly()
    task_12 = flo_dwh_m_track_listen_stat_playlist_dtl_monthly()
    task_13 = flo_dwh_m_chnl_play_type_stat_daily()
    task_14 = flo_dwh_m_track_listen_stat_theme_hr_daily()
    task_15 = flo_dwh_m_flo_listen_stat_novod_hr_daily()
    task_16 = flo_dwh_m_member_login_summary_monthly()
    task_17 = flo_dwh_m_track_listen_rank_daily()
    task_18 = flo_dwh_m_track_listen_rank_weekly()
    task_19 = flo_dwh_m_track_listen_rank_monthly ()
    task_20 = flo_dwh_m_flo_active_stat_daily_d ()
    task_21 = flo_dwh_m_program_list_daily ()
    task_22 = flo_dwh_m_episode_list_daily ()
    task_23 = flo_dwh_m_label_listen_daily ()
    task_25 = flo_dwh_m_track_listen_stat_svc_genre ()
    task_26 = flo_dwh_m_member_login_summary_daily ()
    task_27 = flo_dwh_m_member_login_summary_weekly ()
    task_28 = flo_dwh_m_pass_activity_stat_monthly ()
    task_29 = flo_dwh_m_member_audio_first_listen_daily ()
    task_30 = flo_dwh_m_track_listen_million_stat ()
    task_31 = flo_dwh_m_flo_contents_use_stat()
    task_32 = flo_dwh_m_biz_partner_member_action_cnt_daily()
    task_33 = flo_dwh_m_biz_partner_member_track_listen_stat_daily()
    task_34 = flo_dwh_m_choigorae_vip_member_listen_pass_stat_daily()
    task_35 = flo_dwh_m_playlist_member_retention_weekly()
    task_36 = flo_dwh_sp_m_flo_listen_1min_stat_daily_upload()
    task_37 = flo_dwh_sp_m_flo_listen_1min_stat_weekly_upload()
    task_38 = flo_dwh_sp_m_flo_listen_1min_stat_monthly_upload()
    task_39 = flo_dwh_sp_m_playlist_member_retention_monthly_upload()
    task_40 = flo_dwh_sp_m_playlist_result_indicator_daily_d()
    task_41 = flo_dwh_sp_m_playlist_result_indicator_weekly_d()
    task_42 = flo_dwh_sp_m_playlist_result_indicator_monthly_d()
    task_43 = flo_dwh_sp_m_playlist_result_indicator_yearly_d()
    task_44 = flo_dwh_sp_m_indexboard_mg_listen_daily()

    send_alert = DummyOperator( ##
        task_id='send_alert', dag=dag, 
        on_success_callback = alert.slack_success_alert, 
    )

    section_1 >> task_1 >> task_5 >> task_9 
    section_1 >> task_2 >> task_6 >> task_10 
    section_1 >> task_3 >> task_7 >> task_11 >> task_4 >> task_8 >> task_12 
    section_1 >> task_13 >> task_14 >> task_15 
    section_1 >> task_26 >> task_27 >> task_16 
    section_1 >> task_17 >> task_18 >> task_19 >> task_20 >> task_31 
    section_1 >> task_21 >> task_22 
    section_1 >> task_17 >> task_30 
    section_1 >> [task_23, task_25, task_28, task_29] 
    section_1 >> [task_32, task_33, task_34, task_35]
    section_1 >> [task_36, task_37, task_38, task_39]
    section_1 >> [task_40, task_41, task_42, task_43]

    [task_1, task_2, task_3, task_4, task_5, task_6 , task_7, task_8, task_9, task_10] >> send_alert
    [task_11, task_12, task_13, task_14, task_15, task_16, task_17, task_18, task_19, task_20] >> send_alert 
    [task_21, task_22, task_23, task_25, task_26, task_27, task_28, task_29, task_30] >> send_alert 
    [task_31, task_32, task_33, task_34, task_35, task_36, task_37, task_38, task_39, task_40] >> send_alert 
    [task_41, task_42, task_43, task_44] >> send_alert 
########################################## call Dags #######################################################
