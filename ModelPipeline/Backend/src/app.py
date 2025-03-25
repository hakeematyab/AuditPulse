import warnings
warnings.filterwarnings("ignore")

import os
import sys
import time
import datetime
import logging
import traceback

from flask import Flask, jsonify
from data_validation.data_validation import DataValidator

from auditpulse_flow.main import kickoff
import agentops

from google.cloud import firestore, storage


class AuditPuleApp:
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

        @self.app.route("/generate",methods=["GET"])
        def generate_audit_report():
            try:
                logging.info("Report generation called"+"-"*75)
                start_time = time.time()
                company_name, central_index_key, company_ticker, year = get_update_latest_entry()
                data_validator = DataValidator(company_name, central_index_key, year)
                status, message = data_validator.run_validation()
                if status:
                    validated_inputs = data_validator.auditpulse_validated_inputs
                    company_name = validated_inputs.company_name
                    central_index_key = validated_inputs.company_name
                    company_ticker = validated_inputs.company_ticker
                    year = validated_inputs.year
                    session = agentops.init()
                    kickoff(company_name,
                            central_index_key,
                            company_ticker,
                            year)
                    session.end_session()
                    end_time = time.time()
                    duration = round(end_time - start_time, 2)
                    logging.info(f"Report generation completed successfully in {duration} seconds.")
                    # upload_to_gcp(bucket,gcp_logs_path, log_file_path)
            except Exception as e:
                end_time = time.time()
                duration = round(end_time - start_time, 2)   
                stack_trace = traceback.format_exc()
                logging.error(f"Report generation failed after {duration} seconds.")
                logging.error(f"Error: {str(e)}")
                logging.error(f"Stack Trace:\n{stack_trace}")
                # upload_to_gcp(bucket,gcp_logs_path, log_file_path)
                status = False
                message = str(e) +'\n'+ str(stack_trace)
            
            update_results(status, message)
            return jsonify({    
                "status":"Success!" if status else "Failure!",
                "message":"Report generated!" if status else message}
                )
    def run(self,debug=True):
        self.app.run(debug=debug)

def setup_logging(log_file='logs/run_log.log', log_level=logging.INFO):
    """Set up logging"""
    dir_name = os.path.dirname(log_file)
    os.makedirs(dir_name,exist_ok=True)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file)
        ]
    )
def get_update_latest_entry():
    company_name, central_index_key, company_ticker, year = None, None, None, None
    company_name, central_index_key, company_ticker, year = "Apple Inc.", 320193, "AAPL", "2024"
    return (company_name, 
            central_index_key, 
            company_ticker, 
            year)

def update_results(status, message):
    pass


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
    blob = bucket.blob(gcp_file_path)
    blob.upload_from_filename(local_file_path)



if __name__=="__main__":
    log_file_path = 'logs/run_log.log'
    local_policy_path = 'auditpulse_flow/data/compliance.json'
    gcp_policy_path = 'configs/policy'
    gcp_logs_path = f'logs/deployment/log-{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
    bucket_name = 'auditpulse-data'
    collection_name = 'config'
    document_name = 'deployment'
    phase_names = ['client_acceptance','audit_planning','testing_evidence_gathering','evaluation_reporting']
    setup_logging(log_file_path)
    try:
        logging.info("Run started"+"="*75)
        db_client = firestore.Client(project='auditpulse')
        storage_client = storage.Client(project='auditpulse')
        bucket = storage_client.bucket(bucket_name)
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
        app = AuditPuleApp()
        app.run()
    except Exception as e:
        stack_trace = traceback.format_exc()
        logging.error(f"Run failed.")
        logging.error(f"Error: {str(e)}")
        logging.error(f"Stack Trace:\n{stack_trace}")