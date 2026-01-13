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
import sys
from util.slack_alert import SlackAlert ##
from util.redshift_util import RedshiftUtils
import json,pandas as pd
import s3fs
import sqlalchemy
import requests
import io
import os


###################################################################################
##     수정일   /   수정자    /  수정내용
## 2024.04.03 /   Brett   / 최초 작성. braze api 활용해 데이터 연동 및 테이블 적5


## 로컬 타임존 생성
local_tz = pendulum.timezone("Asia/Seoul")

# slack channel name
alert = SlackAlert('#floda-airflow') ##

## start_date의 tzinfo를 Asia/Seoul로 지정
default_args = {
    'owner': 'DataUnit',
    'depends_on_past': False,
    'start_date': datetime(2023,9,21, tzinfo=local_tz),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries' : 1,
    'catchup' : False,
    'on_failure_callback' : alert.slack_fail_alert
}

dag = DAG(
    dag_id='16_4_airflow_dependency_test_slave_dag',
    description='16_4_airflow_dependency_test_slave_dag',
    default_args=default_args,
    schedule_interval=None, # trigger DAG는 보통 None으로 처리 합니다.
    dagrun_timeout=timedelta(hours=5),
    tags=['test']
)

# Crawling Tasks
def start():
    print('start')
    return "SUCCESS"

def end():
    print('end')
    return "SUCCESS"



def get_secret_value():
    ret = get_secret("arn:aws:secretsmanager:ap-northeast-2:822479450351:secret:test_secret-Q1I9HW")
    print("returned secret: ")
    print(ret)


start = PythonOperator(
    task_id='start',
    python_callable=start,
    dag=dag,
)

end = PythonOperator(
    task_id='end',
    python_callable=end,
    dag=dag,
)

task_get_secret_value = PythonOperator(
    task_id="get_secret_value",
    python_callable=get_secret_value,
    dag=dag,
)

send_alert = DummyOperator( ##
    task_id='send_alert', dag=dag,
    on_success_callback = alert.slack_success_alert,
)

# task_1 >> task_2 >> task_3 >> task_4 >> task_5 >> task_6 >> task_7 >> task_8 >> task_9 >> task_10 >> task_11 >> task_12 >> task_13 >> task_get_secret_value
start >> end >> task_get_secret_value
[start, end] >> send_alert


def ds_add(ads, days):
    """
    >>> ds_add('2022-01-01', 5)
    '2022-01-06'
    >>> ds_add('2022-01-06', -5)
    '2022-01-01'
    """
    ads = datetime.strptime(ads, '%Y-%m-%d')
    if days:
        ads = ads + timedelta(days)
    return ads.isoformat()[:10]

## common function
def execute_sql(sql, timeout=1200):
    rsd = boto3.client('redshift-data')
    resp = rsd.execute_statement(
        ClusterIdentifier='floda-cluster-1',
        Database='flo_data',
        DbUser='floda_etl',
        Sql=sql
    )
    print("execute_statement:",resp)
    print(resp['Id'])
    for x in range(timeout):
        resp = rsd.describe_statement(
            Id=resp['Id']
        )
        time.sleep(30)
        print("describe_statement:",resp)
        if resp['Status'] == 'FINISHED':
            break
        elif resp['Status'] == 'FAILED':
            raise Exception('SQL query failed:' + resp['QueryString'] + ': ' + resp['Error'])

    resp = rsd.get_statement_result(
        Id=resp['Id']
    )
    print("get_statement_result:",resp)
    return "OK"

def get_secret(secret_name):
    # get secret value from "https://ap-northeast-2.console.aws.amazon.com/secretsmanager/home?region=ap-northeast-2#!/secret?name=test_secret"
    region_name = "ap-northeast-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        return get_secret_value_response
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS key.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
