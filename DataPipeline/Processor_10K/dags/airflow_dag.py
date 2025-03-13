import os
import subprocess
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/opt/airflow")
DAGS_DIR = os.path.join(AIRFLOW_HOME, "dags")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 2, 19),
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

def run_extractor():
    script_path = os.path.join(DAGS_DIR, "extractor_10K.py")
    subprocess.run(["python3", script_path], check=True)

def run_processor():
    script_path = os.path.join(DAGS_DIR, "processor_10K.py")
    subprocess.run(["python3", script_path], check=True)

def run_save():
    script_path = os.path.join(DAGS_DIR, "forms_upload_to_gcp_bucket.py")
    subprocess.run(["python3", script_path], check=True)

def run_bias():
    script_path = os.path.join(DAGS_DIR, "bias_mitigation.py")
    subprocess.run(["python3", script_path], check=True)

with DAG(
    '10K_pipeline',
    default_args=default_args,
    description='DAG to run SEC downloader and process 10-K filings',
    schedule_interval=None,
    catchup=False,
) as dag:
    
    task1 = PythonOperator(
        task_id='download_10k_filings',
        python_callable=run_extractor
    )
    
    task2 = PythonOperator(
        task_id='process_10k_filings',
        python_callable=run_processor
    )


    task3 = PythonOperator(
        task_id='bias_code',
        python_callable=run_bias
    )

    task4 = PythonOperator(
        task_id='save_to_bucket',
        python_callable=run_save
    )

    task1 >> task2 >> task3 >> task4
