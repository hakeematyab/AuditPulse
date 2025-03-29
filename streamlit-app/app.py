import streamlit as st
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account
import json
import datetime
import os
from google.cloud.sql.connector import Connector, IPTypes
import pymysql
import sqlalchemy
from sqlalchemy import text
import uuid
import time

# Load credentials from JSON
json_key = ""
with open('creds.json', 'r') as f:
  json_key = json.load(f)

# Function to download file from GCS
def download_file_from_gcs(bucket_name, file_path):
    try:
        credentials = service_account.Credentials.from_service_account_info(
            json_key, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        storage_client = storage.Client(credentials=credentials)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        return blob.download_as_bytes()  # Download file as bytes
    except Exception as e:
        st.error(f"Failed to download file from GCS: {e}")
        return None


# Function to connect to Google Cloud SQL using secrets from secrets.toml
def connect_to_cloud_sql():
    """
    Initializes a connection pool for a Cloud SQL instance of MySQL.
    Uses the Cloud SQL Python Connector package and Streamlit's secrets management.
    """
    # Fetch credentials from secrets.toml
    instance_connection_name = st.secrets["cloud_sql"]["instance_connection_name"]
    db_user = st.secrets["cloud_sql"]["db_user"]
    db_pass = st.secrets["cloud_sql"]["db_pass"]
    db_name = st.secrets["cloud_sql"]["db_name"]

    # Specify whether to use private or public IP for the connection
    ip_type = IPTypes.PRIVATE if st.secrets["cloud_sql"].get("private_ip", False) else IPTypes.PUBLIC

    # Initialize the Cloud SQL Python Connector
    connector = Connector(ip_type=ip_type)

    def getconn() -> pymysql.connections.Connection:
        conn: pymysql.connections.Connection = connector.connect(
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name,
        )
        return conn

    # Create a SQLAlchemy engine using the connection pool
    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
    )

    return pool

# Function to fetch JSON from GCS bucket
def fetch_json_from_gcs(bucket_name, blob_name):
  try:
    credentials = service_account.Credentials.from_service_account_info(
        json_key, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )

    # Initialize storage client with credentials
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    json_data = json.loads(blob.download_as_string())
    return json_data
  except Exception:
    return None  # Don't show error yet; handle later


# Fetch JSON data from GCS
bucket_name = "auditpulse-data"  # Replace with your bucket name
blob_name = "configs/us_public_companies/us_public_companies.json"  # Replace with the path to your JSON file in the bucket
json_data = fetch_json_from_gcs(bucket_name, blob_name)

# Title of the app
st.title("Audit Report Generator")

# Ensure JSON data is available
if json_data:
  valid_cik_strs = [int(item['cik_str']) for item in json_data.values()]

  # Input fields
  username = st.text_input("Enter Username", value="",
                           placeholder="Type your username here")
  central_index_key = st.number_input("Enter Central Index Key", min_value=0,
                                      step=1, value=valid_cik_strs[0])
  current_year = datetime.datetime.now().year
  year = st.number_input("Enter Year", min_value=0, step=1,
                         value=current_year - 1)

  # Validate Central Index Key
  if central_index_key and central_index_key not in valid_cik_strs:
    st.error("Central Index Key isn't correct. Please enter a valid key.")
    st.stop()  # Stops execution if CI Key is invalid

  # Find company info based on cik_str
  company_info = next((item for item in json_data.values() if
                       item['cik_str'] == central_index_key), {})

  # Display company info
  st.write("### Company Information")
  ticker = st.text_area("Ticker", value=company_info.get("ticker", "Unknown"),
                        height=68, disabled=True)
  title = st.text_area("Title", value=company_info.get("title", "Unknown"),
                       height=68, disabled=True)
  # Disable the button until all fields are filled
  if username and central_index_key and year:
    generate_report_disabled = False
  else:
    generate_report_disabled = True

  # Button to generate report
  if st.button("Generate Report",disabled=generate_report_disabled):
    # Create data for report
    company_info = json_data.get(str(central_index_key), {})
    ticker = company_info.get("ticker", "Unknown")
    company_name = company_info.get("title", "Unknown")
    run_at = datetime.datetime.now().strftime(
      "%Y-%m-%d %H:%M:%S")  # Current timestamp
    # Insert data into Cloud SQL database
    try:
      cloud_sql_engine = connect_to_cloud_sql()  # Connect to Cloud SQL

      with cloud_sql_engine.connect() as conn:
        # Start a transaction explicitly
        transaction = conn.begin()

        try:
          run_id = str(uuid.uuid4())

          # Get current timestamp
          run_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

          # Insert data into the database
          insert_query = text("""
                    INSERT INTO runs (run_id, run_at, user_id, cik, ticker, company_name, year)
                    VALUES (:run_id, :run_at, :user_id, :cik, :ticker, :company_name, :year)
                """)

          company_info = json_data.get(str(central_index_key), {})
          ticker = company_info.get("ticker", "Unknown")
          company_name = company_info.get("title", "Unknown")

          # Execute insert query
          conn.execute(insert_query, {
            "run_id": run_id,
            "run_at": run_at,
            "user_id": username,
            "cik": central_index_key,
            "ticker": ticker,
            "company_name": company_name,
            "year": year
          })

          # Commit the transaction explicitly
          transaction.commit()
          st.success(
            f"Report generated and saved to the database with Run ID: {run_id}!")
        except Exception as e:
          # Rollback in case of any error during execution
          transaction.rollback()
          st.error(f"Failed to save report to the database: {e}")
        # Polling for report paths availability
        while True:
          try:
            with cloud_sql_engine.connect() as conn:
              check_query = text("""
                        SELECT audit_report_path, explainability_report_path 
                        FROM runs 
                        WHERE run_id = :run_id;
                    """)

              result = conn.execute(check_query, {"run_id": run_id})
              row = result.fetchone()

              if row and row[0] and row[1]:  # Ensure both paths are available
                audit_report_path = row[0]
                explainability_report_path = row[1]

                st.write("### Reports Available for Download")

                # Button to download Audit Report
                if st.button("Download Audit Report"):
                  audit_file_data = download_file_from_gcs(
                    bucket_name="your-bucket-name", file_path=audit_report_path)
                  if audit_file_data:
                    st.download_button(
                        label="Download Audit Report",
                        data=audit_file_data,
                        file_name="audit_report.pdf",
                        mime="application/pdf"
                    )

                # Button to download Explainability Report
                if st.button("Download Explainability Report"):
                  explainability_file_data = download_file_from_gcs(
                    bucket_name="your-bucket-name",
                    file_path=explainability_report_path)
                  if explainability_file_data:
                    st.download_button(
                        label="Download Explainability Report",
                        data=explainability_file_data,
                        file_name="explainability_report.pdf",
                        mime="application/pdf"
                    )
                break  # Exit the loop once reports are available

              else:
                st.info("Reports are not yet available. Checking again...")
                time.sleep(10)  # Wait for 10 seconds before checking again

          except Exception as e:
            st.error(f"Failed to check report paths: {e}")
            break  # Exit the loop if an error occurs
    except Exception as e:
      st.error(f"Failed to connect to the database: {e}")

    # Convert DataFrame to CSV and store in session state

    #st.session_state.generated_report = csv  # Store CSV in session state
    st.session_state.show_feedback = True  # Enable feedback form
    st.session_state.feedback = None  # Reset feedback choice
    st.session_state.comments = ""  # Reset comments

# Show download button if report is generated
if "generated_report" in st.session_state:
  st.download_button(
      label="Download Report",
      data=st.session_state.generated_report,
      file_name="audit_report.csv",
      mime="text/csv",
  )

# Persistent Feedback Section (Only after "Generate Report" is clicked)
if "show_feedback" in st.session_state and st.session_state.show_feedback:
  st.write("### Feedback")

  # Ensure session state keys exist
  if "feedback" not in st.session_state or st.session_state.feedback not in [
    "👍 Yes", "👎 No"]:
    st.session_state.feedback = "👍 Yes"
  if "comments" not in st.session_state:
    st.session_state.comments = ""

  # Use key for radio button state persistence (avoid manual assignment)
  st.radio(
      "Was this report helpful?",
      ("👍 Yes", "👎 No"),
      index=["👍 Yes", "👎 No"].index(st.session_state.feedback),
      key="feedback"  # This ensures persistence without manual state updates
  )

  # Text area with key for persistence
  st.text_area("Additional Comments", key="comments")

  # Submit Feedback Button
  if st.button("Submit Feedback"):
    st.session_state.feedback_submitted = True
    st.success("Thank you for your feedback!")

elif json_data is None:
  # Show error message only if JSON loading actually failed
  st.error("Failed to load validation data from GCS. Please try again later.")



# Example usage: Fetch data from a table in your database
try:
    cloud_sql_engine = connect_to_cloud_sql()

    with cloud_sql_engine.connect() as conn:
        query = text("SELECT * FROM runs LIMIT 10;")
        result = conn.execute(query)  # Replace with your query

        column_names = result.keys()
        st.write("### Column Names:")
        st.write(column_names)

        st.write("### Sample Data from Cloud SQL")

        rows = result.fetchall()

        if rows:
            df_sql_data = pd.DataFrame(rows, columns=result.keys())
            st.dataframe(df_sql_data)
except Exception as e:
    st.error(f"Failed to connect to Cloud SQL: {e}")