# Processor_10K

## Overview
The **Processor_10K** module in the AuditPulse project is designed to process and extract useful information from SEC Form 10-K filings. This module helps categorize and structure data based on different phases of the audit.

## Features
- Parses Form 10-K filings.
- Extracts key financial and textual information.
- Organizes data for audit automation.

## Prerequisites
Make sure you have the following installed:

- Python 3.8+
- Docker & Docker Compose
- Required dependencies (listed in `requirements.txt`)

## Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/hakeematyab/AuditPulse.git
   cd AuditPulse/DataPipeline/Processor_10K
   ```

2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```


## Running with Docker and Airflow
To build the Docker image and run Apache Airflow, follow these steps:

1. Navigate to the project directory:
   ```sh
   cd AuditPulse/DataPipeline/Processor_10K
   ```

2. Build and start the Docker containers:
   ```sh
   docker-compose up --build -d
   ```

3. Access the Airflow UI by opening your browser and navigating to:
   ```
   http://localhost:8080
   ```

4. Log in using the default credentials:
   ```
   Username: admin
   Password: admin
   ```

5. Trigger the DAG to start processing 10-K files.

### Additional Steps for Running Locally
- The third part of the DAG is responsible for deploying the processed data to Google Cloud Platform (GCP). It transfers data from the Docker container (`/opt/airflow/data`) to the designated GCP bucket.
- Please comment out "task3" in `airflow_dag.py` when running locally
  `docker-compose.yml` is currently set up for running on GCP. Please comment out 
  `image : us-east1-docker.pkg.dev/auditpulse/auditpulse-images/airflow:latest` and uncomment  `build : .` when running locally.


## Output
Processed data will be saved in the specified output directory inside the Docker container at:
```
/opt/airflow/data
```
This data can then be further transferred to a GCP bucket via the Airflow DAG. (When running on GCP)



