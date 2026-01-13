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
import sys
from airflow.decorators import task

###################################################################################
##     수정일   /   수정자    /  수정내용
## 2023.01.19 / Shen / WAU 관련 task_48 flo_dwh_sp_m_member_login_hist_weekly, task_49 flo_dwh_sp_m_member_login_summary_weekly 추가
## 2023.02.01 / Shen / task_49 flo_dwh_sp_m_member_login_summary_weekly 삭제 (DAG 04로 이동)
## 2023.02.08 / Shen / task_49 flo_dwh_m_member_prch_pass_valid_daily 추가
## 2023.02.13 / Blaine / task_50 flo_dwh_m_chnl_eval_stat_daily 추가
## 2023.04.10 / Shen / task_51 flo_dwh_m_auto_payment_pass_login_y_retention_monthly 추가
## 2023.04.12 / Blaine / task_52 flo_log_tb_member_login_hist_daily_upload 추가
## 2023.06.13 / Shen / task_55 flo_dwh_sp_m_pass_issue_status_summary_daily, task_56 flo_dwh_sp_m_member_clause4_agree_daily 추가
## 2023.06.21 / Shen / task_57 flo_dwh_sp_m_newcomer_clause4_agree_summary_daily 추가
## 2023.06.27 / Shen / task_58 , task_59 추가
## 2023.08.17 / Shen / task_60 flo_dwh_m_cover_episode_publish_stat_daily 추가
## 2023.09.14 / Jiny / task_61 flo_dwh_m_flo_login_active_stat_daily 삭제
## 2023.10.26 / Blaine / task_9 flo_dwh_d_member_daily 프로시저 변경
## 2023.11.20 / Blaine / retries 추가
## 2024.02.07 / Shen / task_79 m_member_pass_prch_cnt 추가
## 2024.02.13 / Shen / task_79 m_member_pass_prch_cnt 제거, task_79 m_pass_lt_monthly 추가
## 2024.02.27 / Tina / task_80 flo_dwh_m_pass_sales_stat 추가
## 2024.05.14 / Shen / task_81, task_82 마케팅 이용권 리텐션 관련 2개 작업 추가
## 2024.07.16 / Jiny / task_83 tb_prchs_pass_period, tb_prchs_pass_period_re_prchs_type 추가  
## 2024.07.22 / Brett / execute_sql, ds_add 함수 redshift_util class 에서 호출하도록 변경, skipped alert 추가, get_secret_value 제거,  주석 추가
## 2024.08.26 / Brett / 날짜 관련 로직 -> 메서드 내부호출로 변경, (ds,tomorrow_ds ) -> (**kwargs)로 변경, call_sp.replace() -> 메서드 내부호출로 변경, @task decorator 반영
## 2024.09.24 / Brett / task_84 flo_poc_tb_rising_keyword_ranking_daily task 추가. 정상 수행 확인 후 task_14 flo_poc_tb_rising_keyword_daily 제거 예정
## 2024.09.25 / Brett / task_14 flo_poc_tb_rising_keyword_daily 주석처리한 task 삭제. task_84 -> task_14로 번호 변경
## 2025.01.23 / Jiny / task_84 flo_dw.sp_m_b2b_partner_coupon_pass_list_daily 추가 
## 2025.02.12 / Brett / msp alert 발생용 failure callback 함수 추가 : [alert.slack_fail_alert, alert.msp_fail_alert_webhook]
## 2025.07.07 / Brett / kwargs['ds'] -> kwargs['data_interval_end'] 변경
####################################################################################

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

# Dag 기본 매개변수
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
def flo_poc_tb_member_daily(**kwargs):
    call_sp = """
    call flo_poc.sp_tb_member_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_tb_quit_member_daily(**kwargs):
    call_sp = """
    call flo_poc.sp_tb_quit_member_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_tb_prchs_pass_daily(**kwargs):
    call_sp = """
    call flo_poc.sp_tb_prchs_pass_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_table_total_daily(**kwargs):
    call_sp = """
    call flo_poc.sp_flo_poc_table_total_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_mcp_table_total_daily(**kwargs):
    call_sp = """
    call flo_mcp.sp_flo_mcp_table_total_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_table_video_total_daily(**kwargs):
    call_sp = """
    call flo_poc.sp_flo_poc_table_video_total_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_program_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_program_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_episode_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_episode_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_episode_clip_track_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_episode_clip_track_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_member_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_member ($sdate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_join_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_join_stat_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_music_track_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_music_track_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_themelist_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_themelist_daily_reload ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_playlist_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_playlist_daily_reload ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_tb_rising_keyword_ranking_daily(**kwargs):
    call_sp = """
    call flo_poc.sp_tb_rising_keyword_ranking_daily_upload ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_creator_hist_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_creator_hist_daily_upload ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_login_hist_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_login_hist_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_member_login_hist_weekly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_login_hist_weekly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_login_hist_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_login_hist_monthly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_login_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_login_stat_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_login_stat_weekly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_login_stat_weekly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_login_stat_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_login_stat_monthly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_audio_program_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_audio_program_stat_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_pass_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_pass_stat_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_pass_stat_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_pass_stat_monthly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_pass_issue_status_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_pass_issue_status_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_pass_issue_status_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_pass_issue_status_monthly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_rh_track_status_weekly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_rh_track_status_weekly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_flo_prchs_pass_payment_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_prchs_pass_payment_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_flo_prchs_pass_cancel_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_prchs_pass_cancel_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_psn_member_chnl_ctgr_daily (**kwargs):
    call_sp = """
    call flo_poc.sp_psn_member_chnl_ctgr_daily_upload ($sdate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_badge_issue_daily (**kwargs):
    call_sp = """
    call flo_dwh.sp_m_badge_issue_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_tb_pass_auto_issu_hist_daily (**kwargs):
    call_sp = """
    call flo_poc.sp_tb_pass_auto_issu_hist_daily_upload ($sdate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)
    
@task
def flo_poc_tb_r2k_link_hist_daily (**kwargs):
    call_sp = """
    call flo_poc.sp_tb_r2k_link_hist_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_mcp_tnmm_track_daily (**kwargs):
    call_sp = """
    call flo_mcp.sp_tnmm_track_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_mcp_tnmm_album_daily (**kwargs):
    call_sp = """
    call flo_mcp.sp_tnmm_album_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_mcp_tnmm_video_daily (**kwargs):
    call_sp = """
    call flo_mcp.sp_tnmm_video_daily_upload ($sdate$, $edate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_playlist_dtl_daily (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_playlist_dtl_daily_upload ($sdate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_psn_member_chnl_daily (**kwargs):
    call_sp = """
    call flo_poc.sp_psn_member_chnl_daily_upload ($sdate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_d_producer_daily (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_producer_daily ($sdate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_pass_nonauto_status_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_pass_nonauto_status_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_gcp_gcp_pass_stat_daily(**kwargs):
    call_sp = """
    call flo_gcp.sp_gcp_pass_stat_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_gcp_gcp_pass_issue_stat_daily (**kwargs):
    call_sp = """
    call flo_gcp.sp_gcp_pass_issue_stat_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_tb_creator_daily(**kwargs):
    call_sp = """
    call flo_poc.sp_tb_creator_daily_upload ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_pass_info_biz_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_pass_info_biz_daily_upload ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_flo_pass_sales_payment_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_pass_sales_payment_daily_upload ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_flo_pass_sales_cancel_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_flo_pass_sales_cancel_daily_upload ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_d_svc_category_daily (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_svc_category ($sdate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_prch_pass_valid_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_prch_pass_valid_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_chnl_eval_stat_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_chnl_eval_stat_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_auto_payment_pass_login_y_retention_monthly(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_auto_payment_pass_login_y_retention_monthly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_log_tb_member_login_hist_daily_upload(**kwargs):
    call_sp = """
    call flo_log.sp_tb_member_login_hist_daily_upload ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_pass_issue_new_status_daily (**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_pass_issue_new_status_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_popup_upload_daily (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_popup_upload_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_pass_issue_status_summary_daily (**kwargs):
    call_sp = """
    call flo_dwh.sp_m_pass_issue_status_summary_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_member_clause4_agree_daily (**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_clause4_agree_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_newcomer_clause4_agree_summary_daily (**kwargs):
    call_sp = """
    call flo_dwh.sp_m_newcomer_clause4_agree_summary_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_member_clause4_agree_summary_weekly (**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_clause4_agree_summary_weekly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_member_clause4_agree_summary_monthly (**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_clause4_agree_summary_monthly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_cover_episode_publish_stat_daily (**kwargs):
    call_sp = """
    call flo_dwh.sp_m_cover_episode_publish_stat_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_character (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_character($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_member_dvc (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_member_dvc($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_clip (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_clip($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_creator (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_creator($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_artist (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_artist($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_album (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_album($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_track (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_track($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_video (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_video($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_d_episode_media (**kwargs):
    call_sp = """
    call flo_dwh.sp_d_episode_media($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_mcp_tnac_program_hist (**kwargs):
    call_sp = """
    call flo_mcp.sp_tnac_program_hist($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_mcp_tnac_clip_hist (**kwargs):
    call_sp = """
    call flo_mcp.sp_tnac_clip_hist($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_mcp_tnac_episode_hist (**kwargs):
    call_sp = """
    call flo_mcp.sp_tnac_episode_hist ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_mcp_tnac_episode_media_hist (**kwargs):
    call_sp = """
    call flo_mcp.sp_tnac_episode_media_hist($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_tb_prchs_play_qunty_hist (**kwargs):
    call_sp = """
    call flo_poc.sp_tb_prchs_play_qunty_hist($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_d_track_artist_upload(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_track_artist_upload ($sdate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)


@task
def flo_dwh_sp_d_album_artist_upload(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_album_artist_upload ($sdate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)


@task
def flo_dwh_sp_d_album_style_upload(**kwargs):
    call_sp = """
    call flo_dwh.sp_d_album_style_upload ($sdate$);
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_sp_m_pass_lt_monthly (**kwargs):
    call_sp = """
    call flo_dwh.sp_m_pass_lt_monthly ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_pass_sales_stat(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_pass_sales_stat ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_member_first_auto_payment_pass_info_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_member_first_auto_payment_pass_info_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dwh_m_pass_member_auto_payment_retention_daily(**kwargs):
    call_sp = """
    call flo_dwh.sp_m_pass_member_auto_payment_retention_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_poc_tb_prchs_pass_period_daily(**kwargs):
    call_sp = """
    call flo_poc.sp_tb_prchs_pass_period_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)

@task
def flo_dw_m_b2b_partner_coupon_pass_list_daily(**kwargs):
    call_sp = """
    call flo_dw.sp_m_b2b_partner_coupon_pass_list_daily ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)


@task
def flo_data_user_grant(**kwargs):
    call_sp = """
    call flo_dwh.sp_db_user_grant_daily_upload ($sdate$ );
    """
    executeSql.execute_sql(kwargs['data_interval_end'], call_sp)
########################################## Define python_callable #######################################

########################################## call Dags #######################################################
############################################################################################################
## 실제 Dag 호출                                                                                             ##
## Define python_callable 부분에서 정의된 def를 실제 task로 지정하고 호출                                           ##
############################################################################################################
## DAG 스케줄링 및 기본 정보
with DAG(
    dag_id='01_flo_poc_mcp_daily',
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=5),
    # start_date=days_ago(1),
    schedule_interval='30 5 * * *',
    tags=['flo_poc', 'flo_mcp', 'flo_dwh', 'user grant', 'daily']
) as dag:
## Dag Work 지정
    task_1 = flo_poc_table_total_daily()
    task_2 = flo_mcp_table_total_daily()
    task_3 = flo_poc_tb_member_daily()
    task_4 = flo_poc_tb_quit_member_daily()
    task_5 = flo_poc_tb_prchs_pass_daily()
    task_6 = flo_dwh_d_program_daily()
    task_7 = flo_dwh_d_episode_daily()
    task_8 = flo_dwh_d_episode_clip_track_daily()
    task_9 = flo_dwh_d_member_daily()
    task_10 = flo_dwh_m_member_join_stat_daily()
    task_11 = flo_dwh_d_themelist_daily()
    task_12 = flo_dwh_d_playlist_daily()
    task_13 = flo_dwh_d_music_track_daily()
    task_14 = flo_poc_tb_rising_keyword_ranking_daily()
    task_15 = flo_dwh_m_creator_hist_daily()
    task_16 = flo_dwh_m_member_login_hist_daily()
    task_17 = flo_dwh_m_login_stat_daily()
    task_18 = flo_dwh_m_login_stat_weekly()
    task_19 = flo_dwh_m_login_stat_monthly()
    task_20 = flo_dwh_m_audio_program_stat_daily()
    task_21 = flo_dwh_m_pass_stat_daily()
    task_22 = flo_dwh_m_pass_stat_monthly()
    task_23 = flo_dwh_m_rh_track_status_weekly()
    task_24 = flo_dwh_m_flo_prchs_pass_cancel_daily()
    task_25 = flo_dwh_m_flo_prchs_pass_payment_daily()
    task_26 = flo_poc_psn_member_chnl_ctgr_daily()
    task_27 = flo_dwh_m_badge_issue_daily()
    task_28 = flo_poc_tb_pass_auto_issu_hist_daily()
    task_29 = flo_dwh_m_pass_issue_status_daily()
    task_30 = flo_dwh_m_pass_issue_status_monthly()
    task_31 = flo_poc_tb_r2k_link_hist_daily()
    task_32 = flo_poc_table_video_total_daily()
    task_33 = flo_mcp_tnmm_track_daily()
    task_34 = flo_mcp_tnmm_album_daily()
    task_35 = flo_mcp_tnmm_video_daily()
    task_36 = flo_dwh_m_member_login_hist_monthly()
    task_37 = flo_dwh_d_playlist_dtl_daily()
    task_38 = flo_poc_psn_member_chnl_daily()
    task_39 = flo_dwh_m_pass_nonauto_status_daily()
    task_40 = flo_dwh_sp_d_producer_daily()
    task_41 = flo_gcp_gcp_pass_stat_daily()
    task_42 = flo_gcp_gcp_pass_issue_stat_daily()
    task_43 = flo_poc_tb_creator_daily()
    task_44 = flo_dwh_d_pass_info_biz_daily()
    task_45 = flo_dwh_m_flo_pass_sales_payment_daily()
    task_46 = flo_dwh_m_flo_pass_sales_cancel_daily()
    task_47 = flo_dwh_sp_d_svc_category_daily()
    task_48 = flo_dwh_sp_m_member_login_hist_weekly()
    task_49 = flo_dwh_m_member_prch_pass_valid_daily()
    task_50 = flo_dwh_m_chnl_eval_stat_daily()
    task_51 = flo_dwh_m_auto_payment_pass_login_y_retention_monthly()
    task_52 = flo_log_tb_member_login_hist_daily_upload()
    task_53 = flo_dwh_m_member_pass_issue_new_status_daily()
    task_54 = flo_dwh_d_popup_upload_daily()
    task_55 = flo_dwh_sp_m_pass_issue_status_summary_daily()
    task_56 = flo_dwh_sp_m_member_clause4_agree_daily()
    task_57 = flo_dwh_sp_m_newcomer_clause4_agree_summary_daily()
    task_58 = flo_dwh_sp_m_member_clause4_agree_summary_weekly()
    task_59 = flo_dwh_sp_m_member_clause4_agree_summary_monthly()
    task_60 = flo_dwh_m_cover_episode_publish_stat_daily()
    task_62 = flo_dwh_d_character()
    task_63 = flo_dwh_d_member_dvc()
    task_64 = flo_dwh_d_clip()
    task_65 = flo_dwh_d_creator()
    task_66 = flo_dwh_d_artist()
    task_67 = flo_dwh_d_album()
    task_68 = flo_dwh_d_track()
    task_69 = flo_dwh_d_video()
    task_70 = flo_dwh_d_episode_media()
    task_71 = flo_mcp_tnac_program_hist()
    task_72 = flo_mcp_tnac_clip_hist()
    task_73 = flo_mcp_tnac_episode_hist()
    task_74 = flo_mcp_tnac_episode_media_hist()
    task_75 = flo_poc_tb_prchs_play_qunty_hist()
    task_76 = flo_dwh_sp_d_track_artist_upload()
    task_77 = flo_dwh_sp_d_album_artist_upload()
    task_78 = flo_dwh_sp_d_album_style_upload()
    task_79 = flo_dwh_sp_m_pass_lt_monthly()
    task_80 = flo_dwh_m_pass_sales_stat()
    task_81 = flo_dwh_m_member_first_auto_payment_pass_info_daily()
    task_82 = flo_dwh_m_pass_member_auto_payment_retention_daily()   
    task_83 = flo_poc_tb_prchs_pass_period_daily()  
    task_84 = flo_dw_m_b2b_partner_coupon_pass_list_daily()  
     
    
    task_flo_data_user_grant = flo_data_user_grant()

    send_alert = DummyOperator( ##
        task_id='send_alert', dag=dag,
        on_success_callback = alert.slack_success_alert,
        )

## Data Work Flow
    # flo_poc, flo_mcp 관련
    task_1 >> task_44 >> task_32 >> task_7 >> task_6 >> task_8 >> task_26 >> [task_11, task_12] >> task_47 >> task_23 >> task_13 >> task_flo_data_user_grant 
    task_2 >> task_33 >> task_34 >> task_35 >> task_7 >> task_6 >> task_flo_data_user_grant
    # 공개리스트 메타
    task_12 >> task_37 >> task_flo_data_user_grant
    # tb_prchs_pass 관련
    [task_1, task_5] >> task_83 >> task_7 >> [task_6, task_49, task_81] >> task_82 >> task_79 >> task_84 >> task_flo_data_user_grant 
    [task_1, task_5, task_83, task_9, task_44] >> task_56 >> task_57 >> [task_58, task_59] >> task_31 >> task_24 >> task_25 >> task_flo_data_user_grant
    # gcp 이용권 관련
    [task_1, task_5, task_83, task_44] >> task_41 >> task_42 >> task_flo_data_user_grant
    # 회원테이블 및 마트 관련
    [task_3, task_4] >> task_9 >> task_10 >> task_flo_data_user_grant
    # flo_poc rising keyword & d_popup 24.09.25 flo_poc.tb_rising_keyword 삭제
    task_14 >> task_flo_data_user_grant
    task_1 >> task_54 >> task_flo_data_user_grant
    # flo_poc psn_member_chnl 관련
    task_38 >> [task_43, task_9] >> task_15 >> task_50 >> task_flo_data_user_grant
    # flo_dwh d_producer
    task_1 >> task_38 >> task_40 >> task_flo_data_user_grant
    # flo_dwh m_login 관련
    [task_1, task_9] >> task_52 >> task_16 >> [task_17,task_36,task_48] >> task_18 >> task_19 >> task_flo_data_user_grant
    [task_16, task_49, task_81] >> task_82 >> task_51 >> task_flo_data_user_grant
    # flo_dwh m_audio_program_stat_daily
    task_7 >> [task_6, task_9] >> task_20 >> task_60 >> task_flo_data_user_grant
    # 일별 이용권 발급 현황
    [task_1, task_2, task_5, task_83, task_9, task_31, task_44] >> task_45 >> task_46 >> task_21 >> task_22 >> task_29 >> task_55 >> task_30 >> task_39 >> task_53 >> task_80 >> task_flo_data_user_grant
    # 일별 뱃지 현황
    task_1 >> task_27 >> task_28 >> task_flo_data_user_grant
    # 디멘젼
    task_2 >> task_71 >> task_72 >> task_73 >> task_74 >> task_flo_data_user_grant
    task_1 >> task_62 >> task_63 >> task_64 >> task_75 >> task_flo_data_user_grant
    [task_1, task_2] >> task_65 >> task_66 >> task_67 >> task_68 >> task_69 >> task_flo_data_user_grant
    [task_64, task_68] >> task_70 >> task_flo_data_user_grant
    [task_1, task_2] >> task_76 >> task_77 >> task_78 >> task_flo_data_user_grant

    #slack alert
    [task_1, task_2, task_3, task_4, task_5, task_6 , task_7, task_8, task_9, task_10] >> send_alert
    [task_11, task_12, task_13, task_14, task_15, task_16, task_17, task_18, task_19, task_20] >> send_alert
    [task_21, task_22, task_23, task_24, task_25, task_26, task_27, task_28, task_29, task_30] >> send_alert
    [task_31, task_32, task_33, task_34, task_35, task_36, task_37, task_38, task_39, task_40] >> send_alert
    [task_41, task_42, task_43, task_44, task_45, task_46, task_47, task_48, task_49, task_50] >> send_alert
    [task_51, task_52, task_53, task_54, task_55, task_56, task_57, task_58, task_59, task_60] >> send_alert
    [task_62, task_63, task_64, task_65, task_66, task_67, task_68, task_69, task_70] >> send_alert
    [task_71, task_72, task_73, task_74, task_75, task_76, task_77, task_78, task_79, task_80] >> send_alert
    [task_81, task_82, task_83, task_84] >> send_alert
