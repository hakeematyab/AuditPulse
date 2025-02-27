# Use Airflow base image
FROM apache/airflow:2.6.2-python3.8

# Install additional dependencies
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libpq-dev

# Switch back to Airflow user
USER airflow

# Set working directory
WORKDIR /opt/airflow

# Copy DAGs, plugins, and requirements
COPY dags/ /opt/airflow/dags/
COPY requirements.txt /opt/airflow/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Airflow environment variable
ENV AIRFLOW_HOME=/opt/airflow
