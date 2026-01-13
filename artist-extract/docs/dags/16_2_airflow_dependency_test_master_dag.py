from airflow import DAG
from airflow.decorators import task
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
import sys
from util.slack_alert import SlackAlert ##
from util.redshift_util import RedshiftUtils
#from airflow.models import DagRun
from airflow.models.variable import Variable
from mstrio.connection import Connection
from mstrio.distribution_services import Event
import pprint


###################################################################################
##     수정일   /   수정자    /  수정내용
## 2024.08.06 /   Blaine  / 테스트 용도로 변경
## 2024.08.30 /   Brett  / mstr connect test 용도로 변경
## 연동 테스트

# slack channel name
alert = SlackAlert('#floda-airflow') ##

## 로컬 타임존 생성
local_tz = pendulum.timezone("Asia/Seoul")

# dag_id 저장
dag_id = sys._getframe().f_code.co_filename.split('.')[0].split('/')[-1]
# 클래스 호출
executeSql = RedshiftUtils(dag_id)

# Normal call style
deployment_type = 'dev'
try :
    deployment_type = Variable.get("deployment_type")
except Exception:
    pass

DEFAULT_ARGS = {
    'owner': 'DataUnit',
    'depends_on_past': False,
    'start_date': datetime(2023,9,22, tzinfo=local_tz),
    'email': ['g-data@dreamus.io'],
    'email_on_failure': False,
    'email_on_retry': False,
    #'on_failure_callback' : alert.slack_fail_alert,
    #'on_success_callback' : alert.slack_skipped_alert, ## 상태값은 success 인데 내무적으로 success가 아닌 skipped등 다른 상태값일때 알림
    'retry_delay' : timedelta(minutes=1)
}

@task
def mstr_connect_test (**kwargs):
    v_url = Variable.get("v_url") # https://floda.data.music-flo.io/MicroStrategyLibrary/api
    #v_username = Variable.get("v_username") # administrator
    #v_password = Variable.get("v_password") # floda123
    v_project_id = Variable.get("v_project_id") # 5CE467247E4ADF4D6CD8CBA372745E72
    v_trigger_id = Variable.get("v_trigger_id") # EFE6E61C4F7E190F41575A9334D633A7
    IDENTITY_TOKEN = "TokenEAABAA7E8247869AB68DC2B2AF7C5D69"
    print('v_url :',v_url)
    #print('v_username :',v_username)
    #print('v_password :',v_password)
    print('v_project_id :',v_project_id)
    print('v_trigger_id :',v_trigger_id)
    #conn = Connection(base_url=v_url, username=v_username, password=v_password, project_id=v_project_id , login_mode=1)
    conn = Connection(base_url=v_url, identity_token=IDENTITY_TOKEN, project_id=v_project_id)
    event = Event(conn,id=v_trigger_id)
    event.trigger() # trigger call


 ## DAG 스케줄링 및 기본 정보
with DAG(
    dag_id='16_2_airflow_dependency_test_master_dag',
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=5),
    # start_date=days_ago(1),
    schedule_interval=None,
    tags=['test']
) as dag:
## Dag Work 지정

    task_1 = mstr_connect_test()

    '''
    send_alert = DummyOperator( ##
        task_id='send_alert', dag=dag,
        on_success_callback = alert.slack_success_alert,
    )
    '''
# task_1 >> task_2 >> task_3 >> task_4 >> task_5 >> task_6 >> task_7 >> task_8 >> task_9 >> task_10 >> task_11 >> task_12 >> task_13 >> task_get_secret_value
task_1
