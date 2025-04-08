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

import base64
from flask import Flask, jsonify, request
from data_validation.data_validation import DataValidator

from auditpulse_flow.main import kickoff
import agentops

from google.cloud import firestore, storage
import mysql.connector


class AuditPulseApp:
    def __init__(self,):
        self.app = Flask(__name__)
        self.setup_endpoints()

    def setup_endpoints(self,):
        @self.app.route("/",methods=["GET"])
        def health_check():
            return jsonify({    
                "status":"OK",
                "message":"AuditPulse Live!"}
                )

        @self.app.route("/generate",methods=["POST"])
        def generate_audit_report():
            try:
                start_time = time.time()
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                gcp_audit_report_path = f'generated_reports/audit_report/audit_report_{timestamp}.md'
                gcp_visualization_path = f'generated_reports/visualization_report/visualization_{timestamp}.html'
                gcp_logs_path = f'generated_reports/logs/log_{timestamp}'

                visualization_file = f'output/visualization/visualization_{timestamp}.html'
                audit_report_file = f'output/final_report/audit_report_{timestamp}.md'
                run_log_file = f"logs/run_{timestamp}.txt"
                debug_log_file =f"logs/debug_{timestamp}.log"

                setup_logging(run_log_file, debug_log_file)
                logging.info("Report generation called"+"-"*75)
                try:
                    envelope = request.get_json()
                    print(envelope)
                except:
                    pass
                try:
                    envelope = request.get_data()
                    print(envelope)
                except:
                    pass
                return jsonify({    
                "status":"Test"
                })
                run_id, company_name, central_index_key, company_ticker, year = get_input_data(envelope)
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
                    update_status(query, values)
                    cleanup_dirs('output')
                    cleanup_dirs('logs')
                    setup_dirs()
                    session = agentops.init()
                    kickoff(company_name,
                            central_index_key,
                            company_ticker,
                            year)
                    session.end_session()
                    end_time = time.time()
                    duration = round(end_time - start_time, 2)
                    compile_report(audit_report_file)
                    # compile_visualization(visualization_file)
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
                            f"Report generation completed successfully in {duration} seconds.",
                            run_id
                            )
                    update_status(query, values)
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
                        fail_message,
                        run_id
                        )
                update_status(query, values)
                status = False
                message = str(e) +'\n'+ str(stack_trace)
            return jsonify({    
                "status":"Success!" if status else "Failure!",
                "message":"Report generated!" if status else message[:100]}
                )
    def run(self,host='0.0.0.0', port=5000, debug=True):
        self.app.run(host=host, port=port, debug=debug, use_reloader=False)

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
    message = envelope.get('message',None)
    if not message:
        raise ValueError("Input data absent.")
    data = base64.b64decode(message['data']).decode('utf-8')
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
                        SET status=%s, audit_report_path=%s, explainability_report_path=%s, logs_path=%s, message=%s
                        WHERE run_id=%s
                      """
                    )
    }
    return mapping.get(type,None)

def update_status(query,values):
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

def compile_report(final_report_path):
    base_path = 'output'
    if not os.path.exists(os.path.dirname(final_report_path)):
        os.makedirs(os.path.dirname(final_report_path),exist_ok=True)
    phase_task_mapping = {
                        'client_acceptance':['client_background_task.md', 'financial_risk_task.md', 'engagement_scope_task.md'],
                        'audit_planning':['preliminary_engagement_task.md','business_risk_task.md','internal_control_task.md','audit_strategy_task.md'],
                        'testing_evidence':['substantive_testing_task.md','control_testing_task.md','analytical_procedures_task.md','evidence_documentation_task.md'],
                        'evaluation_reporting':['evidence_evaluation_task.md','misstatement_analysis_task.md','conclusion_formation_task.md','audit_report_drafting_task.md']
                        }
    
    with open(final_report_path, 'w') as final_report_file:
        for phase in phase_task_mapping.keys():
            for task_file in phase_task_mapping[phase]:
                file = os.path.join(base_path, phase, task_file)
                if not os.path.exists(file):
                    raise ValueError(f"Missing phase: {phase}")
                with open(file, 'r') as task_report_file:
                    final_report_file.write(task_report_file.read().lstrip('```markdown').lstrip('```').rstrip('```'))
                    final_report_file.write(f'\n')

def compile_visualization(logs_path, final_visualization_path):
    base_path = 'output'
    # TODO: Call visualization function and compile all into one file.

def setup_dirs():
    phases = [
            'client_acceptance',
            'audit_planning',
            'testing_evidence',
            'evaluation_reporting'
            ]
    for phase in phases:
        os.makedirs(os.path.join('output',phase),exist_ok=True)
    os.makedirs('logs')

def cleanup_dirs(temp_dir):
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

if __name__=="__main__":
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
    setup_logging(run_log_file, debug_log_file)
    try:
        logging.info("Run started"+"="*75)
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
                logging.error(f"Error at {local_phase_prompt_path}")
                logging.error(str(e))
        app = AuditPulseApp()
        app.run()
    except Exception as e:
        stack_trace = traceback.format_exc()
        logging.error(f"Run failed.")
        logging.error(f"Error: {str(e)}")
        logging.error(f"Stack Trace:\n{stack_trace}")
