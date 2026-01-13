##appsflyer load to redshift
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
import json,pandas as pd
import s3fs
import sqlalchemy
import requests
import io
import os
from airflow.decorators import task
import sys
from util.slack_alert import SlackAlert ##
from util.redshift_util import RedshiftUtils
import re

###################################################################################
##     수정일   /   수정자    /  수정내용
## 2024.04.03 /   Brett   / 최초 작성.
## 2024.09.11 /   Brett   / 테스트용 Dag로 변경



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
    'start_date': datetime(2024,9,21, tzinfo=local_tz),
    'email': ['g-data@dreamus.io'],
    'email_on_failure': False,
    'email_on_retry': False,
    'on_failure_callback' : alert.slack_fail_alert,
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
def lambda_api_call(**kwargs):
    # 호출할 URL
    url = "https://j73evcj1ba.execute-api.ap-northeast-2.amazonaws.com/default/GoogleSpreadSheetUploadToS3"
    # 연동 target directory, sheet id 설정
    params = {
    "targetDir": "platform_business",
    "sheetId": "sales_data_201903-202408,sga_expenses" #시트가 여러개일 경우 쉼표(,)로 구분.
    }
    target_dir = params['targetDir']
    sheet_id = params['sheetId']
    # parameter 전달을 위해 str타입으로 변경
    payload = f'targetDir={target_dir}&sheetId={sheet_id}'
    print(payload)
    # api 호출
    response = requests.request("GET", url, params=payload)
    # 결과 메세지 출력
    print(response.text)
    #api session close
    requests.session().close()

    # 금액 부분 , 제거하여 재업로드
    # aws s3 연결
    s3 = boto3.client('s3')
    sheet_list = sheet_id.split(',')
    for sheet in sheet_list:
        if 'sales_data' in sheet :
            sheet_nm = sheet
            partition = sheet_nm[-6:]
            bucket = 'floda-data'
            obj = s3.get_object(Bucket=bucket,Key="manual_upload/platform_business/sales_data/yyyymm=" + partition + "/" + sheet_nm + ".tsv")
            read_tsv = io.BytesIO(obj["Body"].read())
            df = pd.read_csv(read_tsv, delimiter='\t')
            df['credit'] = df['credit'].str.replace(',', '')
            df['debit'] = df['debit'].str.replace(',', '')
            df_csv = df.to_csv(sep="\t", index=False)

            #print(df_csv)
            s3.put_object(Bucket=bucket, Body=df_csv, Key="manual_upload/platform_business/sales_data/yyyymm=" + partition + "/" + sheet_nm + ".tsv")
        else :
            pass

@task
def rs_flo_input_sales_data_add_partition(**kwargs):
    call_sp = """
    alter table rs_flo_input.sales_data add if not exists partition (yyyymm = $sdate$) location 's3://floda-data/manual_upload/platform_business/sales_data/yyyymm=$pdate$/';
    """
    call_sp = call_sp.replace('$sdate$',"'"+kwargs['ds_nodash'][:6]+"'")
    call_sp = call_sp.replace('$pdate$',kwargs['ds_nodash'][:6])
    executeSql.execute_sql(kwargs['ds'], call_sp)


# 16_3_airflow_dependency_test_slave_dag
########################################## Define python_callable #######################################

########################################## call Dags #######################################################
############################################################################################################
## 실제 Dag 호출                                                                                             ##
## Define python_callable 부분에서 정의된 def를 실제 task로 지정하고 호출                                           ##
############################################################################################################
with DAG(
    dag_id='16_3_airflow_dependency_test_slave_dag',
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=5),
    schedule_interval=None,
    tags=['settlement', 'settlement_result', 'daily']
) as dag:

    task_1 = lambda_api_call()
    task_2 = rs_flo_input_sales_data_add_partition()

    send_alert = DummyOperator( ##
        task_id='send_alert', dag=dag,
        on_success_callback = alert.slack_success_alert,
    )

    task_1 >> task_2

    [task_1, task_2] >> send_alert
########################################## call Dags #######################################################
