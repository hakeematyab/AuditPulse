# Use the official Apache Airflow image
FROM apache/airflow:2.6.2

# Set working directory
WORKDIR /opt/airflow

# Install system dependencies required for sec-edgar-downloader
RUN apt-get update && apt-get install -y build-essential python3-dev

# Upgrade pip, setuptools, and wheel before installing dependencies
RUN pip install --upgrade pip setuptools wheel

# Copy DAGs and install requirements
COPY dags/ /opt/airflow/dags/
COPY requirements.txt /opt/airflow/requirements.txt

# Install dependencies including sec-edgar-downloader
RUN pip install --no-cache-dir -r requirements.txt

# Set Airflow environment variable
ENV AIRFLOW_HOME=/opt/airflow
