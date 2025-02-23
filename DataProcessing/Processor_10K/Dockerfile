# Use the official Apache Airflow image
FROM apache/airflow:2.6.2

# Set working directory inside the container
WORKDIR /opt/airflow

# Copy the DAGs, plugins, and script files
COPY dags/ /opt/airflow/dags/
COPY plugins/ /opt/airflow/plugins/
COPY requirements.txt /opt/airflow/requirements.txt

# Install necessary dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Airflow home environment variable
ENV AIRFLOW_HOME=/opt/airflow

# Ensure necessary NLTK data is available
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('wordnet'); nltk.download('omw-1.4')"
