import time
import datetime
import logging
import traceback
import os
import sys
import shutil
import json
from typing import List

from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
from pydantic import BaseModel, Field
from groq import Groq
import instructor

from google.cloud import firestore, storage

class AuditRule(BaseModel):
    """Data model for audit rules."""
    rule_id: str = Field(..., description="Unique identifier for the rule, formatted as PCAOB-XXXX")
    standard: str = Field(..., description="The PCAOB auditing standard reference")
    description: str = Field(..., description="Concise explanation of what the rule entails")
    enforcement_guidelines: List[str] = Field(..., description="Actionable steps required to ensure compliance")

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

def chunk_pdf(input_pdf_path, output_dir, chunk_size=50):
    """
    Splits a PDF into smaller chunks of a specified number of pages.

    Args:
        input_pdf_path (str): The file path of the input PDF.
        output_dir (str): The directory where the chunked PDFs will be saved.
        chunk_size (int, optional): The number of pages per chunk. Defaults to 50.

    Returns:
        list: A list of file paths for the generated PDF chunks.
    """
    reader = PdfReader(input_pdf_path)
    total_pages = len(reader.pages)
    
    chunks = []
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        chunk_pages = reader.pages[i:i + chunk_size]
        
        for page in chunk_pages:
            writer.add_page(page)
        
        output_pdf_path = f"{output_dir}/chunk_{i // chunk_size + 1}.pdf"
        with open(output_pdf_path, "wb") as output_pdf:
            writer.write(output_pdf)
        chunks.append(output_pdf_path)
    return chunks


def pdf2text(pdf_path):
    """
    Extracts text from a PDF using PyMuPDF.

    Args:
        pdf_path (str): The file path of the PDF.

    Returns:
        str: The extracted text from the PDF.
    """
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text.strip()

def generate_rules(prompt, text, client, model, sleeptime, max_retries=5) -> List[AuditRule]:
    """
    Generates structured audit rules using the OpenAI API based on the provided text and prompt.

    Args:
        prompt (str): The prompt providing context or instructions.
        text (str): The text extracted from the PDF.
        client (OpenAI): The OpenAI client instance.
        model (str, optional): The model to be used for generating rules.

    Returns:
        list: A list of audit rules generated by the OpenAI API.
    """
    retries = 0

    while retries < max_retries:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                response_model=List[AuditRule],
                temperature=0.1,
                max_tokens=1024
            )

            logging.info("200 OK - Successfully retrieved JSON response.")
            time.sleep(sleeptime)
            return response

        except Exception as e:
            error_message = str(e)
            logging.error(f"Error: {error_message}")

            if "400" in error_message:
                logging.warning("400 Bad Request - Retrying the same chunk immediately.")
                retries += 1
                continue

            elif "413" in error_message:
                logging.warning(f"413 Payload Too Large - Waiting {sleeptime} seconds before retrying.")
                time.sleep(sleeptime)
                retries += 1
                continue

            else:
                logging.error(f"Unexpected API Error: {error_message}")
                break

    logging.error("Max retries reached. Skipping this chunk.")
    return []

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


def save_policy(policy, output_path):
    """
    Saves the generated policy as a JSON file.

    Args:
        policy (list): A list of generated policy rules.
        output_path (str): File path where the JSON policy will be saved.

    Returns:
        None
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(policy, f, indent=4)

def cleanup(dir):
    """
    Deletes a directory and its contents.

    Args:
        dir (str): The directory path to be removed.

    Returns:
        None
    """
    shutil.rmtree(dir)


def main():
    """Main function that orchestrates policy generation, storage, and Firestore updates."""
    log_file_path = 'logs/run_log.log'
    collection_name = 'config'
    document_name = 'policy'
    local_standards_path = './inputs/auditing_standards.pdf'
    bucket_name = 'auditpulse-data'
    gcp_policy_path = 'configs/policy'
    gcp_logs_path = 'logs/policy'
    prompt_path = './inputs/prompt.txt'
    output_dir = './outputs'
    temp_dir = './temp'
    max_retries = 10
    policy = []

    setup_logging(log_file_path)
    start_time = time.time()
    logging.info("Run started "+"-"*25)
    try:
        llm_client = instructor.from_groq(Groq(), mode=instructor.Mode.JSON)
        db_client = firestore.Client(project='auditpulse')
        storage_client = storage.Client(project='auditpulse')
        bucket = storage_client.bucket(bucket_name)

        policy_doc = get_document(db_client, collection_name, document_name)
        model_type = policy_doc.get('active_model_type')
        model = policy_doc.get('active_model_id')
        gcp_standards_path = policy_doc.get('active_standards_path')
        gcp_policy_prompt_path = policy_doc.get('active_prompt_path')
        latest_version = policy_doc.get('latest_version')
        chunk_size = int(policy_doc.get('text_chunk_size'))
        sleeptime = int(policy_doc.get('sleeptime'))
        max_retries = policy_doc.get('max_retries', max_retries)
        current_version = int(latest_version[1:]) + 1

        local_output_path = os.path.join(output_dir, f'policy_v{current_version}.json')
        gcp_output_path = f"{gcp_policy_path}/policy_v{current_version}.json"

        download_from_gcp(bucket, gcp_standards_path, local_standards_path)
        download_from_gcp(bucket, gcp_policy_prompt_path, prompt_path)

        pdf_chunks = chunk_pdf(local_standards_path, temp_dir, chunk_size)
        if not pdf_chunks:
            raise ValueError("No valid PDF chunks found.")
        
        with open(prompt_path, 'r') as f:
            prompt = f.read()

        for pdf in pdf_chunks:
            text = pdf2text(pdf)
            rules = generate_rules(prompt, text, llm_client, model, sleeptime, max_retries)
            policy.extend(rules)
        policy = [rule.dict() for rule in policy]

        save_policy(policy, local_output_path)
        upload_to_gcp(bucket,gcp_output_path, local_output_path)
        updated_collection = {
                            'active_version': f'v{current_version}',
                            'latest_version': f'v{current_version}',
                            'active_version_path': gcp_output_path,
                            'latest_version_path': gcp_output_path,
                            f'versions.v{current_version}': {
                                        'created_at': firestore.SERVER_TIMESTAMP,
                                        'policy_path': gcp_output_path,
                                        'standards_path':gcp_standards_path,
                                        'model_type': model_type,
                                        'model_id': model
                                                    }
                            }
        update_collection(db_client, collection_name, document_name, updated_collection)
        cleanup(temp_dir)
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        logging.info(f"Policy generation completed successfully in {duration} seconds.")
        upload_to_gcp(bucket,gcp_logs_path, log_file_path)

    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)   
        stack_trace = traceback.format_exc()
        logging.error(f"Run failed after {duration} seconds.")
        logging.error(f"Error: {str(e)}")
        logging.error(f"Stack Trace:\n{stack_trace}")
        upload_to_gcp(bucket,gcp_logs_path, log_file_path)


if __name__ == '__main__':
    main()