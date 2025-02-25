# ✅ Use a lightweight Airflow image
FROM apache/airflow:2.6.2-python3.8

# ✅ Switch to root only when needed
USER root

# ✅ Install only essential dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ✅ Switch back to airflow user
USER airflow

# ✅ Set working directory inside the container
WORKDIR /opt/airflow

# ✅ Upgrade pip with a specific version (avoids unnecessary dependencies)
RUN pip install --upgrade pip==23.1.2 setuptools wheel

# ✅ Copy DAGs and install dependencies
COPY dags/ /opt/airflow/dags/
COPY requirements.txt /opt/airflow/requirements.txt

# ✅ Install dependencies with optimized pip settings
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Set Airflow environment variable
ENV AIRFLOW_HOME=/opt/airflow
