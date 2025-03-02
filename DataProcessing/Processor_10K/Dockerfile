# Use Apache Airflow base image
FROM apache/airflow:2.6.2-python3.8

# Install additional system dependencies
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpq-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV AIRFLOW_HOME=/opt/airflow
ENV PYTHONUNBUFFERED=1

# Switch back to Airflow user
USER airflow

# Set working directory
WORKDIR $AIRFLOW_HOME

# Copy DAGs, Plugins, and Requirements
COPY dags/ $AIRFLOW_HOME/dags/
COPY plugins/ $AIRFLOW_HOME/plugins/
COPY requirements.txt $AIRFLOW_HOME/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

