import warnings
warnings.filterwarnings("ignore")

import os
import sys
import time
import datetime
import logging
import traceback
import json
import glob
import shutil
import re

import base64
from data_validation.data_validation import DataValidator
from log_visualization.vizCreator import createVisualizations

from google.cloud import firestore, storage
from google.cloud import pubsub_v1
import mysql.connector
from multiprocessing import Process

class TeeStream:
    def __init__(self, original_stream, log_file):
        self.original_stream = original_stream
        self.log_file = log_file
        
    def write(self, data):
        self.original_stream.write(data)
        self.original_stream.flush()
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(data)
            
    def flush(self):
        self.original_stream.flush()

def setup_logging(run_log_file, debug_log_file, log_level=logging.INFO):
    """Set up logging that captures all stdout and stderr"""
    # Set up normal logging for your custom log messages
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(debug_log_file)
        ]
    )
    
    # Redirect stdout to both console and file
    sys.stdout = TeeStream(sys.stdout, run_log_file)
    sys.stderr = TeeStream(sys.stderr, debug_log_file)
    
def get_input_data(envelope):
    data = envelope.data
    data = json.loads(data)
    run_id = data.get('run_id')
    company_name = data.get('company_name')
    central_index_key = data.get('central_index_key')
    company_ticker = data.get('company_ticker')
    year = data.get('year')
    return (run_id,
            company_name, 
            central_index_key, 
            company_ticker, 
            year)

def get_document(db_client, collection_name, document_name):
    """
    Retrieves a document from the Firestore database.

    Args:
        db_client (firestore.Client): Firestore database client instance.
        collection_name (str): The name of the Firestore collection. Default is 'config'.
        document_name (str): The name of the document to retrieve. Default is 'policy'.

    Returns:
        dict: The document data if found, else returns a default policy structure.
    """
    policy_collection = db_client.collection(collection_name).document(document_name)
    policy_document = policy_collection.get()
    if policy_document.exists:
        return policy_document.to_dict()
    else:
        raise ValueError('Policy document does not exist.')

def get_query(type):
    mapping = {
        'status_update':(
                        """
                        UPDATE runs
                        SET status=%s
                        WHERE run_id=%s
                        """
                        ),
        'run_update':(
                      """
                        UPDATE runs
                        SET status=%s, audit_report_path=%s, explainability_report_path=%s, logs_path=%s, prompt_path=%s, message=%s
                        WHERE run_id=%s
                      """
                    )
    }
    return mapping.get(type,None)

def update_status(mysql_cursor, mysql_conn, query,values):
    mysql_cursor.execute(query,values)
    mysql_conn.commit()

def update_collection(db_client, collection_name, document_name, updated_collection):
    """
    Updates the Firestore policy document with the new version details.

    Args:
        db_client (firestore.Client): Firestore database client instance.
        collection_name (str): The Firestore collection where the policy is stored. Default is 'config'.
        document_name (str): The name of the Firestore document to update. Default is 'policy'.
        version (int): The version number for the new policy.
        gcp_file_path (str): The path where the policy file is stored in GCP Cloud Storage.
        standards_path (str): The path where related policy standards are stored.

    Returns:
        None
    """
    policy_collection = db_client.collection(collection_name).document(document_name)
    policy_collection.update(updated_collection)

def download_from_gcp(bucket, gcp_file_path, local_file_path):
    # if os.path.exists(local_file_path):
    #     return
    blob = bucket.blob(gcp_file_path)
    blob.download_to_filename(local_file_path)

def upload_to_gcp(bucket, gcp_file_path, local_file_path):
    """
    Uploads a policy file to Google Cloud Storage.

    Args:
        bucket (google.cloud.storage.Bucket): GCP Storage bucket instance.
        gcp_file_path (str): Destination path in GCP Cloud Storage.
        local_file_path (str): Local file path of the policy file.

    Returns:
        None
    """
    if not os.path.exists(local_file_path):
        os.makedirs(os.path.dirname(local_file_path),exist_ok=True)
        with open(local_file_path, 'w') as f:
            f.write('Hello World!')
    blob = bucket.blob(gcp_file_path)
    blob.upload_from_filename(local_file_path)

def clean_markdown(content):
    content = re.sub(r'^```\w*\s*\n', '', content)
    content = re.sub(r'^```\s*\n', '', content)
    content = re.sub(r'\n```\s*$', '', content)
    return content

def compile_report(base_path, final_report_path):
    if not os.path.exists(os.path.dirname(final_report_path)):
        os.makedirs(os.path.dirname(final_report_path),exist_ok=True)
    phase_task_mapping = {
                        'client_acceptance':['client_background_task.md', 'financial_risk_task.md', 'engagement_scope_task.md'],
                        'audit_planning':['preliminary_engagement_task.md','business_risk_task.md','internal_control_task.md','audit_strategy_task.md'],
                        'testing_evidence':['control_testing_task.md','financial_statement_analysis_task.md','significant_transaction_testing_task.md','fraud_risk_assessment_task.md'],
                        'evaluation_reporting':['evidence_evaluation_task.md','financial_statement_compliance_task.md','going_concern_task.md','audit_opinion_task.md']
                        }
    
    with open(final_report_path, 'w') as final_report_file:
        for phase in phase_task_mapping.keys():
            for task_file in phase_task_mapping[phase]:
                file = os.path.join(base_path, phase, task_file)
                if not os.path.exists(file):
                    raise ValueError(f"Missing phase: {phase}. File: {file}")
                with open(file, 'r') as task_report_file:
                    content = task_report_file.read().lstrip('```markdown').lstrip('```').rstrip('```')
                    content = clean_markdown(content)
                    final_report_file.write(content)
                    final_report_file.write(f'\n')

def compile_visualization(base_path, logs_path, final_visualization_path):
    createVisualizations(logs_path, final_visualization_path)

def setup_dirs(output_path):
    phases = [
            'client_acceptance',
            'audit_planning',
            'testing_evidence',
            'evaluation_reporting'
            ]
    for phase in phases:
        os.makedirs(os.path.join(output_path,phase),exist_ok=True)

def cleanup_dirs(temp_dir):
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

def subscriber(process_idx, gcp_prompt_path):
    from auditpulse_flow.main import kickoff
    import agentops
    def generate_audit_report(envelope, bucket, mysql_cursor, mysql_conn):
        try:
            start_time = time.time()
            run_id, company_name, central_index_key, company_ticker, year = get_input_data(envelope)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            run_log_file = f"logs/run_{run_id}_{timestamp}.txt"
            debug_log_file =f"logs/debug_{run_id}_{timestamp}.log"

            setup_logging(run_log_file, debug_log_file)
            logging.info("Report generation called"+"-"*75)

            gcp_audit_report_path = f'generated_reports/audit_report/audit_report_{run_id}_{timestamp}.md'
            gcp_visualization_path = f'generated_reports/visualization_report/visualization_{run_id}_{timestamp}.html'
            gcp_logs_path = f'generated_reports/logs/log_{run_id}_{timestamp}'

            visualization_file = f'output/visualization/visualization_{run_id}_{timestamp}.html'
            audit_report_file = f'output/final_report/audit_report_{run_id}_{timestamp}.md'
            base_output_path = f'output/{run_id}'

            data_validator = DataValidator(str(company_name), str(central_index_key), str(year))
            status, message = data_validator.run_validation()
            if status:
                validated_inputs = data_validator.auditpulse_validated_inputs
                company_name = validated_inputs.company_name
                central_index_key = validated_inputs.company_name
                company_ticker = validated_inputs.company_ticker
                year = validated_inputs.year
                query = get_query("status_update")
                values = (
                        "running",
                        run_id
                        )
                update_status(mysql_cursor, mysql_conn, query, values)
                setup_dirs(base_output_path)
                session = agentops.init()
                kickoff(run_id,
                        company_name,
                        central_index_key,
                        company_ticker,
                        year)
                session.end_session()
                end_time = time.time()
                duration = round(end_time - start_time, 2)
                compile_report(base_output_path, audit_report_file)
                compile_visualization(base_output_path, run_log_file, visualization_file)
                logging.info(f"Report generation completed successfully in {duration} seconds.")
                upload_to_gcp(bucket,gcp_audit_report_path, audit_report_file)
                upload_to_gcp(bucket,gcp_visualization_path, visualization_file)
                upload_to_gcp(bucket,gcp_logs_path, debug_log_file)
                query = get_query("run_update")
                values = (
                        "completed",
                        gcp_audit_report_path,
                        gcp_visualization_path,
                        gcp_logs_path,
                        gcp_prompt_path,
                        f"Report generation completed successfully in {duration} seconds.",
                        run_id
                        )
                update_status(mysql_cursor, mysql_conn, query, values)
            else:
                raise ValueError(f"Inputs not valid.\nDetails: {message}")
        except Exception as e:
            end_time = time.time()
            duration = round(end_time - start_time, 2)   
            stack_trace = traceback.format_exc()
            logging.error(f"Report generation failed after {duration} seconds.")
            logging.error(f"Error: {str(e)}")
            logging.error(f"Stack Trace:\n{stack_trace}")
            upload_to_gcp(bucket,gcp_logs_path, debug_log_file)
            query = get_query("run_update")
            fail_message = str(e)[:50]
            values = (
                    'failed',
                    '',
                    '',
                    gcp_logs_path,
                    gcp_prompt_path,
                    fail_message,
                    run_id
                    )
            update_status(mysql_cursor, mysql_conn, query, values)

    subscriber_path = 'projects/auditpulse/subscriptions/deployment-request-queue-sub'
    storage_client = storage.Client(project='auditpulse')
    bucket = storage_client.bucket('auditpulse-data')
    mysql_conn = mysql.connector.connect(
        host='34.46.191.121',
        port=3306,
        user='root',
        database='auditpulse',
        password=os.getenv('MYSQL_GCP_PASS')
    )
    mysql_cursor = mysql_conn.cursor()
    subscriber = pubsub_v1.SubscriberClient()
    timeout = float('inf')
    start_time = 0
    while True:
        try:
            response = subscriber.pull(
                            request={
                                "subscription": subscriber_path,
                                "max_messages": 1,
                                "return_immediately": True,
                            },
                        )
            subscriber.acknowledge({"subscription": subscriber_path, "ack_ids": [response.received_messages[0].ack_id]})
            start_time = 0
            print(f"Process {process_idx+1} picked up a task.")
            generate_audit_report(response.received_messages[0].message, bucket, mysql_cursor, mysql_conn)
            print(f"Process {process_idx+1} completed the task.")
        except:
            if start_time==0:
                start_time = time.perf_counter()
            elif time.perf_counter() - start_time > timeout:
                print(f"Timeout. Process {process_idx+1} exiting.")
                break
            else:
                pass

def start_worker(num_workers, gcp_prompt_path):
    workers = []
    for i in range(num_workers):
        print(f'Process {i+1} started.')
        p = Process(target=subscriber, args=(i, gcp_prompt_path))
        p.start()
        workers.append(p)
    for i, p in enumerate(workers):
        p.join()
        print(f'Process {i+1} completed.')


def main():
    num_workers = 2
    log_dir = 'logs'
    local_policy_path = 'auditpulse_flow/data/compliance.json'
    gcp_policy_path = 'configs/policy'
    gcp_logs_path = f'logs/deployment/log-{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
    bucket_name = 'auditpulse-data'
    collection_name = 'config'
    document_name = 'deployment'
    phase_names = ['client_acceptance','audit_planning','testing_evidence_gathering','evaluation_reporting']
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_log_file = f"logs/run_{timestamp}.txt"
    debug_log_file =f"logs/debug_{timestamp}.log"
    # setup_logging(run_log_file, debug_log_file)
    try:
        print("Run started"+"="*75)
        db_client = firestore.Client(project='auditpulse')
        storage_client = storage.Client(project='auditpulse')
        bucket = storage_client.bucket(bucket_name)
        mysql_conn = mysql.connector.connect(
            host='34.46.191.121',
            port=3306,
            user='root',
            database='auditpulse',
            password=os.getenv('MYSQL_GCP_PASS')
        )
        mysql_cursor = mysql_conn.cursor()
        deployment_config = get_document(db_client, collection_name, document_name)
        gcp_policy_path = deployment_config.get('active_policy_path')
        gcp_prompt_path = deployment_config.get('active_prompts_path')
        phase_prompt_paths = [gcp_prompt_path+'/'+phase_name+'/'+yml_name for phase_name in phase_names for yml_name in ['agents.yaml','tasks.yaml']]
        
        download_from_gcp(bucket, gcp_policy_path, local_policy_path)
        for phase_prompt_path in phase_prompt_paths:
            phase_name = os.path.basename(os.path.dirname(phase_prompt_path))
            file_name = os.path.basename(phase_prompt_path)
            local_phase_prompt_path = os.path.join('auditpulse_flow','crews',phase_name+'_crew','config',file_name)
            try:
                download_from_gcp(bucket, phase_prompt_path, local_phase_prompt_path)
            except Exception as e:
                print(f"Error at {local_phase_prompt_path}")
                print(str(e))
        start_worker(num_workers, gcp_prompt_path)
        cleanup_dirs('output')
        cleanup_dirs('logs')
    except Exception as e:
        stack_trace = traceback.format_exc()
        print("Run failed.")
        print(f"Error: {str(e)}")
        print(f"Stack Trace:\n{stack_trace}")

if __name__=="__main__":
    main()