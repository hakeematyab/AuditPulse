import os
from google.cloud import storage

def upload_folder_to_gcs(local_folder, bucket_name, destination_folder):
    """Uploads a folder to Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    for root, _, files in os.walk(local_folder):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_folder)
            gcs_path = os.path.join(destination_folder, relative_path)

            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(local_path)
            print(f"File {local_path} uploaded to {gcs_path}")

# Usage example
AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/opt/airflow")
local_folder = os.path.join(AIRFLOW_HOME, "data/sec-edgar-filings")
bucket_name = "auditpulse-data"
destination_folder = "processed-data/sec-edgar-filings"

upload_folder_to_gcs(local_folder, bucket_name, destination_folder)
