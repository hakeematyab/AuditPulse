# Use an Airflow image that supports Python 3.8
FROM apache/airflow:2.6.2-python3.8

# Switch to root to install dependencies
USER root

# Install system dependencies required for Airflow and Python packages
RUN apt-get update && apt-get install -y build-essential python3-dev libpq-dev

# ✅ Install NVIDIA CUDA Toolkit and cuDNN (only if GPU is available)
RUN if command -v nvidia-smi; then \
      apt-get install -y --no-install-recommends nvidia-cuda-toolkit libcudnn8; \
    fi

# Switch back to Airflow user
USER airflow

# Set working directory inside the container
WORKDIR /opt/airflow

# Upgrade pip, setuptools, and wheel
RUN pip install --upgrade pip setuptools wheel

# Copy DAGs and install dependencies
COPY dags/ /opt/airflow/dags/
COPY requirements.txt /opt/airflow/requirements.txt

# ✅ Ensure correct dependencies are installed
RUN pip install --no-cache-dir -r requirements.txt

# Set Airflow environment variable
ENV AIRFLOW_HOME=/opt/airflow
