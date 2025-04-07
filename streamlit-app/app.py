import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account
import json
import datetime
from google.cloud.sql.connector import Connector, IPTypes

import sqlalchemy
from sqlalchemy import text
import uuid
import time
from google.cloud import pubsub_v1


# Load credentials from JSON file
def load_credentials(file_path):
  """Load service account credentials from a JSON file."""
  try:
    with open(file_path, 'r') as f:
      return json.load(f)
  except Exception as e:
    st.error(f"Failed to load credentials: {e}")
    return None


# Initialize global variables
json_key = load_credentials('creds.json')


# Function to download a file from Google Cloud Storage (GCS)
def download_file_from_gcs(bucket_name, file_path):
  """Download a file from GCS."""
  try:
    credentials = service_account.Credentials.from_service_account_info(
        json_key, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    return blob.download_as_bytes()
  except Exception as e:
    st.error(f"Failed to download file from GCS: {e}")
    return None


# Function to fetch JSON data from GCS
def fetch_json_from_gcs(bucket_name, blob_name):
  """Fetch JSON data from GCS."""
  try:
    credentials = service_account.Credentials.from_service_account_info(
        json_key, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return json.loads(blob.download_as_string())
  except Exception as e:
    st.error(f"Failed to fetch JSON data from GCS: {e}")
    return None


# Function to connect to Google Cloud SQL using Streamlit secrets
def connect_to_cloud_sql():
  """Create a connection pool for Google Cloud SQL."""
  try:
    instance_connection_name = st.secrets["cloud_sql"][
      "instance_connection_name"]
    db_user = st.secrets["cloud_sql"]["db_user"]
    db_pass = st.secrets["cloud_sql"]["db_pass"]
    db_name = st.secrets["cloud_sql"]["db_name"]

    ip_type = IPTypes.PRIVATE if st.secrets["cloud_sql"].get("private_ip",
                                                             False) else IPTypes.PUBLIC

    connector = Connector(ip_type=ip_type)

    def getconn():
      return connector.connect(
          instance_connection_name,
          "pymysql",
          user=db_user,
          password=db_pass,
          db=db_name,
      )

    return sqlalchemy.create_engine("mysql+pymysql://", creator=getconn)
  except Exception as e:
    st.error(f"Failed to connect to Cloud SQL: {e}")
    return None


# Function to monitor report status and provide download options
def monitor_status_and_download(run_id, bucket_name):
  """Monitor the status of the report and enable downloads when ready."""
  try:
    cloud_sql_engine = connect_to_cloud_sql()

    while True:
      with cloud_sql_engine.connect() as conn:
        # Query the database for status and report paths
        query = text("""
                    SELECT status, audit_report_path, explainability_report_path 
                    FROM runs 
                    WHERE run_id = :run_id;
                """)
        result = conn.execute(query, {"run_id": run_id})
        row = result.fetchone()

        if row:
          status, audit_report_path, explainability_report_path = row

          if status == "completed":
            # Download reports from GCS
            audit_file_data = download_file_from_gcs(bucket_name,
                                                     audit_report_path)
            explainability_file_data = download_file_from_gcs(bucket_name,
                                                              explainability_report_path)

            if audit_file_data and explainability_file_data:
              st.success("Reports are ready for download!")

              # Save session state to ensure buttons persist
              st.session_state["audit_file_data"] = audit_file_data
              st.session_state[
                "explainability_file_data"] = explainability_file_data

            break  # Exit the loop once reports are ready

          elif status == "failed":
            st.error("Failed to generate reports.")
            break

          else:
            st.info("Waiting for reports to be generated...")
            time.sleep(30)  # Poll every 30 seconds

  except Exception as e:
    st.error(f"An error occurred while monitoring the report status: {e}")

def publish_to_pubsub(run_id, username, central_index_key, company_name, ticker, year):
    """Publish a message to a Google Pub/Sub topic."""
    try:
        # Define the Pub/Sub topic path
        topic_path = 'projects/auditpulse/topics/deployment-request-queue'

        # Create the message payload
        data = {
            'run_id': run_id,
            'user_id': username,
            'central_index_key': central_index_key,
            'company_name': company_name,
            'ticker': ticker,
            'year': year
        }

        # Convert the data to JSON and encode it as bytes
        jsonstring = json.dumps(data)
        jsonstring = jsonstring.encode('utf-8')

        # Initialize the Pub/Sub Publisher client
        publisher = pubsub_v1.PublisherClient()

        # Publish the message
        future = publisher.publish(topic_path, jsonstring)
        future.result()  # Ensure the publish succeeds before proceeding

        print(f"Message published to Pub/Sub for Run ID: {run_id}")

    except Exception as e:
        print(f"Failed to publish message to Pub/Sub: {e}")
# Function to generate report and save it in Cloud SQL
def generate_report(username, central_index_key, year, json_data):
  """Generate audit report and save it in Cloud SQL."""
  try:
    cloud_sql_engine = connect_to_cloud_sql()

    if not cloud_sql_engine:
      return

    run_id = str(uuid.uuid4())
    run_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    company_info = json_data.get(str(central_index_key), {})

    insert_query = text("""
            INSERT INTO runs (run_id, run_at, user_id, cik, ticker, company_name, year)
            VALUES (:run_id, :run_at, :user_id, :cik, :ticker, :company_name, :year)
        """)

    with cloud_sql_engine.begin() as conn:
      conn.execute(insert_query, {
        "run_id": run_id,
        "run_at": run_at,
        "user_id": username,
        "cik": central_index_key,
        "ticker": company_info.get("ticker", "Unknown"),
        "company_name": company_info.get("title", "Unknown"),
        "year": year,
      })

    st.session_state["current_run_id"] = run_id
    st.success(f"Report generation initiated! Run ID: {run_id}")
    # Publish data to Pub/Sub
    publish_to_pubsub(run_id, username, central_index_key,
                      company_info.get("title", "Unknown"),
                      company_info.get("ticker", "Unknown"), year)

    # Monitor the status of the report and enable downloads when ready
    monitor_status_and_download(run_id, bucket_name="auditpulse-data")

  except Exception as e:
    st.error(f"Failed to generate report: {e}")

def submit_feedback(run_id, liked_report, additional_feedback):
    """Submit feedback to the database for a specific run ID."""
    try:
        # Connect to the Cloud SQL database
        cloud_sql_engine = connect_to_cloud_sql()

        if not cloud_sql_engine:
            st.error("Failed to connect to the database.")
            return

        # Get the current timestamp
        feedback_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update feedback in the database
        update_query = text("""
            UPDATE runs
            SET feedback_1 = :additional_feedback, feedback_2 = :liked_report
            WHERE run_id = :run_id
        """)

        with cloud_sql_engine.begin() as conn:
            conn.execute(update_query, {
                "run_id": run_id,
                "liked_report": liked_report,
                "additional_feedback": additional_feedback,
                "feedback_time": feedback_time,
            })

        st.success("Feedback submitted successfully.")

    except Exception as e:
        st.error(f"An error occurred while submitting feedback: {e}")


# Main application logic
def main():
  # Initialize session state for feedback tracking and downloads
  if "audit_file_data" not in st.session_state:
    st.session_state["audit_file_data"] = None

  if "explainability_file_data" not in st.session_state:
    st.session_state["explainability_file_data"] = None

  # Load validation data from GCS
  bucket_name = "auditpulse-data"
  blob_name = "configs/us_public_companies/us_public_companies.json"
  json_data = fetch_json_from_gcs(bucket_name, blob_name)

  # Title of the app
  st.title("Audit Report Generator")

  if not json_data:
    st.error("Failed to load validation data from GCS.")
    return

  valid_cik_strs = [int(item['cik_str']) for item in json_data.values()]

  # Input fields
  username = st.text_input("Enter Username",
                           placeholder="Type your username here")
  central_index_key = st.number_input("Enter Central Index Key", min_value=0,
                                      step=1, value= valid_cik_strs[0])
  current_year = datetime.datetime.now().year
  year = st.number_input("Enter Year", min_value=0, step=1,
                         value=current_year - 1)

  # Validate Central Index Key
  if central_index_key not in valid_cik_strs:
    st.error("Central Index Key isn't correct. Please enter a valid key.")
    return

  # Display company information based on Central Index Key
  company_info = next((item for item in json_data.values() if
                       item['cik_str'] == central_index_key), {})

  st.write("### Company Information")
  ticker = company_info.get("ticker", "Unknown")
  title = company_info.get("title", "Unknown")

  st.text_area("Ticker", value=ticker, height=68, disabled=True)
  st.text_area("Title", value=title, height=68, disabled=True)

  if username and central_index_key and year:
    # Generate report button logic
    if st.button("Generate Report"):
      generate_report(username, central_index_key, year, json_data)

  # Show download buttons if files are ready in session state
  if st.session_state["audit_file_data"] and st.session_state[
    "explainability_file_data"]:
    st.download_button(
        label="Download Audit Report",
        data=st.session_state["audit_file_data"],
        file_name="audit_report.md",
        mime="text/markdown"
    )

    st.download_button(
        label="Download Explainability Report",
        data=st.session_state["explainability_file_data"],
        file_name="explainability_report.md",
        mime="text/markdown"
    )
    # Feedback Section
    st.write("---")  # Horizontal line for separation
    st.write("### Feedback")

    # Radio button for "Did you like the report?"
    liked_report = st.radio("Did you like the report?", ["Yes", "No"], key="liked_report")

    # Text area for additional feedback
    additional_feedback = st.text_area(
        label="Additional Feedback",
        placeholder="Provide your feedback here...",
        key="additional_feedback"
    )

    # Submit feedback button
    if st.button("Submit Feedback"):
        # Retrieve run_id from session state or other logic
        run_id = st.session_state.get("current_run_id", None)

        if not run_id:
            st.error("Run ID not found. Feedback cannot be submitted.")
        else:
            submit_feedback(run_id, liked_report, additional_feedback)

if __name__ == "__main__":
  main()
