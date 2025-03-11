import streamlit as st
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account
import json
import datetime


json_key = ""
with open('creds.json', 'r') as f:
    json_key = json.load(f)

# Function to fetch JSON from GCS bucket
def fetch_json_from_gcs(bucket_name, blob_name):
    try:
        print(0)
        credentials = service_account.Credentials.from_service_account_info(
            json_key, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

        # Initialize storage client with credentials
        storage_client = storage.Client(credentials=credentials)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        json_data = json.loads(blob.download_as_string())
        return json_data
    except Exception as e:
        st.error(f"Error fetching JSON from GCS: {e}")
        return None

# Fetch JSON data from GCS
bucket_name = "auditpulse-data"  # Replace with your bucket name
blob_name = "configs/us_public_companies/us_public_companies.json"  # Replace with the path to your JSON file in the bucket
json_data = fetch_json_from_gcs(bucket_name, blob_name)

if json_data:
    valid_cik_strs = [int(item['cik_str']) for item in json_data.values()]

    # Title of the app
    st.title("Audit Report Generator")

    # Input fields
    central_index_key = st.number_input("Enter Central Index Key", min_value=0, step=1, value=valid_cik_strs[0])

    current_year = datetime.datetime.now().year
    year = st.number_input("Enter Year", min_value=0, step=1, value= current_year - 1)

    # Validate Central Index Key
    if central_index_key and central_index_key not in valid_cik_strs:
        st.error("Central Index Key isn't correct. Please enter a valid key.")
        st.stop()  # Stops execution if CI Key is invalid
    # Find company info based on cik_str
    company_info = next((item for item in json_data.values() if item['cik_str'] == central_index_key), {})

    # Display company info
    st.write("### Company Information")
    ticker = st.text_area("Ticker", value=company_info.get("ticker", "Unknown"), height=68, disabled=True)
    title = st.text_area("Title", value=company_info.get("title", "Unknown"), height=68, disabled=True)

    # Button to generate report
    if st.button("Generate Report"):
        # Placeholder for report generation logic
        company_info = json_data.get(str(central_index_key), {})
        data = {
            "Central Index Key": [central_index_key],
            "Year": [year],
            "Ticker": [company_info.get("ticker", "Unknown")],
            "Title": [company_info.get("title", "Unknown")]
        }
        df = pd.DataFrame(data)

        # Convert DataFrame to CSV
        csv = df.to_csv(index=False).encode('utf-8')

        # Downloadable report
        st.download_button(
            label="Download Report",
            data=csv,
            file_name="audit_report.csv",
            mime="text/csv",
        )

        if st.session_state.get("download_report", False):
            # Feedback section
            st.write("### Feedback")
            feedback = st.radio("Was this report helpful?", ("👍 Yes", "👎 No"))
            comments = st.text_area("Additional Comments")
            if st.button("Submit Feedback"):
                st.success("Thank you for your feedback!")
        else:
            # Set session state to True after download
            # This part is tricky because Streamlit doesn't directly notify when a download happens.
            # You might need to implement a workaround or use a different approach for tracking downloads.
            # For now, let's assume the feedback section will appear immediately after clicking "Generate Report".
            st.write("### Feedback")
            feedback = st.radio("Was this report helpful?", ("👍 Yes", "👎 No"))
            comments = st.text_area("Additional Comments")
            if st.button("Submit Feedback"):
                st.success("Thank you for your feedback!")
else:
    st.error("Failed to load validation data from GCS.")
