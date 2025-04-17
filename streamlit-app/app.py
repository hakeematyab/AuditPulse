import streamlit as st
from google.cloud import storage
import os
import json
import datetime
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
from sqlalchemy import text
import uuid
import time
from google.cloud import pubsub_v1

st.set_page_config(page_title="Audit Pulse", layout="centered")
# GCS utilities
def download_file_from_gcs(bucket_name, file_path):
    try:
        client = storage.Client()
        blob = client.bucket(bucket_name).blob(file_path)
        return blob.download_as_bytes()
    except Exception as e:
        st.error(f"Failed to download file from GCS: {e}")
        return None

def fetch_json_from_gcs(bucket_name, blob_name):
    try:
        client = storage.Client()
        blob = client.bucket(bucket_name).blob(blob_name)
        return json.loads(blob.download_as_string())
    except Exception as e:
        st.error(f"Failed to fetch JSON data from GCS: {e}")
        return None

# Cloud SQL connection
def connect_to_cloud_sql():
    try:
        # Read config from environment variables
        instance_connection_name = "auditpulse:us-central1:auditpulse"
        db_user = "root"
        db_pass = os.getenv('MYSQL_GCP_PASS')
        db_name = "auditpulse"
        ip_type = os.environ.get("IP_TYPE", "PUBLIC").upper()  # Optional: set to "PRIVATE" if needed

        connector = Connector(ip_type=IPTypes.PRIVATE if ip_type == "PRIVATE" else IPTypes.PUBLIC)

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

# Pub/Sub message
def publish_to_pubsub(run_id, username, central_index_key, company_name, ticker, year):
    try:
        topic_path = 'projects/auditpulse/topics/deployment-request-queue'
        data = json.dumps({
            'run_id': run_id,
            'user_id': username,
            'central_index_key': central_index_key,
            'company_name': company_name,
            'ticker': ticker,
            'year': year
        }).encode('utf-8')

        pubsub_v1.PublisherClient().publish(topic_path, data).result()
    except Exception as e:
        print(f"Failed to publish message to Pub/Sub: {e}")

# Monitor and download
def monitor_status_and_download(run_id, bucket_name, start_time):
    try:
        engine = connect_to_cloud_sql()
        with st.spinner("⏳ Generating reports, please wait (est. 15 minutes)..."):
            while True:
                with engine.connect() as conn:
                    query = text("SELECT status, audit_report_path, explainability_report_path FROM runs WHERE run_id = :run_id;")
                    row = conn.execute(query, {"run_id": run_id}).fetchone()

                    if row:
                        status, audit_path, explain_path = row
                        if status == "completed":
                            audit_data = download_file_from_gcs(bucket_name, audit_path)
                            explain_data = download_file_from_gcs(bucket_name, explain_path)

                            if audit_data and explain_data:
                                st.session_state["audit_file_data"] = audit_data
                                st.session_state["explainability_file_data"] = explain_data
                                total_time = time.time() - start_time
                                minutes, seconds = divmod(int(total_time), 60)
                                st.success(f"✅ Reports are ready! Total time: {minutes} minutes {seconds} seconds")
                            break
                        elif status == "failed":
                            st.error("❌ Report generation failed.")
                            break

                    time.sleep(30)
    except Exception as e:
        st.error(f"An error occurred while monitoring report status: {e}")

# Generate report
def generate_report(username, central_index_key, year, json_data):
    try:
        engine = connect_to_cloud_sql()
        if not engine:
            return

        run_id = str(uuid.uuid4())
        company = json_data.get(str(central_index_key), {})
        status = "queued"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        insert_query = text("""
            INSERT INTO runs (run_id, run_at, user_id, cik, ticker, company_name, year, status)
            VALUES (:run_id, :run_at, :user_id, :cik, :ticker, :company_name, :year, :status)
        """)

        with engine.begin() as conn:
            conn.execute(insert_query, {
                "run_id": run_id,
                "run_at": timestamp,
                "user_id": username,
                "cik": central_index_key,
                "ticker": company.get("ticker", "Unknown"),
                "company_name": company.get("title", "Unknown"),
                "year": year,
                "status": status,
            })

        st.session_state["current_run_id"] = run_id
        print(f"🚀 Report generation started! Run ID: {run_id}")

        publish_to_pubsub(run_id, username, central_index_key,
                          company.get("title", "Unknown"),
                          company.get("ticker", "Unknown"), year)

        monitor_status_and_download(run_id, "auditpulse-data", time.time())

    except Exception as e:
        st.error(f"Failed to generate report: {e}")

# Submit feedback
def submit_feedback(run_id, liked_report, additional_feedback):
    try:
        engine = connect_to_cloud_sql()
        if not engine:
            st.error("Failed to connect to database.")
            return

        query = text("""
            UPDATE runs
            SET feedback_1 = :additional_feedback, feedback_2 = :liked_report
            WHERE run_id = :run_id
        """)

        with engine.begin() as conn:
            conn.execute(query, {
                "run_id": run_id,
                "liked_report": liked_report,
                "additional_feedback": additional_feedback,
            })

        st.success("✅ Feedback submitted. Thank you!")

    except Exception as e:
        st.error(f"An error occurred while submitting feedback: {e}")

# Main UI
def main():
    st.title("📊 Audit Pulse")
    st.markdown("Generate and download audit and explainability reports for US public companies.")

    if "audit_file_data" not in st.session_state:
        st.session_state["audit_file_data"] = None
    if "explainability_file_data" not in st.session_state:
        st.session_state["explainability_file_data"] = None

    json_data = fetch_json_from_gcs("auditpulse-data", "configs/us_public_companies/us_public_companies.json")
    if not json_data:
        st.error("Failed to load company data.")
        return
    st.divider()
    st.markdown("### 🧾 Enter Report Details")

    valid_ciks = [int(item['cik_str']) for item in json_data.values()]

    col1, col2 = st.columns(2)
    username = col1.text_input("👤 Username", placeholder="Type your username")
    central_index_key = col2.number_input("🏢 Central Index Key", min_value=0, value=valid_ciks[4], step=1)

    current_year = datetime.datetime.now().year
    year = st.number_input("📅 Year", min_value=1990, max_value=current_year, value=current_year - 1, step=1)

    if central_index_key not in valid_ciks:
        st.error("Invalid Central Index Key. Please enter a valid one.")
        return

    company_info = next((item for item in json_data.values() if item['cik_str'] == central_index_key), {})

    st.markdown("### 🏷️ Company Information")
    st.text_input("Ticker", value=company_info.get("ticker", "Unknown"), disabled=True)
    st.text_input("Company Name", value=company_info.get("title", "Unknown"), disabled=True)

    st.divider()
    if username and central_index_key and year:
        if st.button("📥 Generate Report"):
            generate_report(username, central_index_key, year, json_data)

    if st.session_state["audit_file_data"] and st.session_state["explainability_file_data"]:
        st.divider()
        st.markdown("### 📄 Download Reports")
        st.download_button("⬇️ Audit Report", st.session_state["audit_file_data"], file_name="audit_report.md", mime="text/markdown")
        st.download_button("⬇️ Explainability Report", st.session_state["explainability_file_data"], file_name="explainability_report.md", mime="text/markdown")

        st.divider()
        st.markdown("### 💬 Feedback")
        liked_report = st.radio("Did you like the report?", ["Yes", "No"])
        feedback = st.text_area("Any additional feedback?", placeholder="Your thoughts...")

        if st.button("✅ Submit Feedback"):
            run_id = st.session_state.get("current_run_id")
            if run_id:
                submit_feedback(run_id, liked_report, feedback)
            else:
                st.error("Run ID not found. Please generate a report first.")

if __name__ == "__main__":
    main()