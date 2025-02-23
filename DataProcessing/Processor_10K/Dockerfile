# Use a Python 3.8+ base image instead of Airflow's default
FROM python:3.8-slim

# Install system dependencies for Airflow and sec-edgar-downloader
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libpq-dev

# Install Apache Airflow
RUN pip install --upgrade pip setuptools wheel
RUN pip install apache-airflow==2.6.2  # Specify Airflow version

# Set working directory inside the container
WORKDIR /opt/airflow

# Copy DAGs and install requirements
COPY dags/ /opt/airflow/dags/
COPY requirements.txt /opt/airflow/requirements.txt

# Install dependencies including sec-edgar-downloader
RUN pip install --no-cache-dir -r requirements.txt

# Set Airflow environment variable
ENV AIRFLOW_HOME=/opt/airflow
