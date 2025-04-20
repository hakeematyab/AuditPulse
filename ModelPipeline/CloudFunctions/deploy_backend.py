import functions_framework
import os
import mysql.connector
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import requests    


@functions_framework.http
def deploy_backend(request):
    def get_auth_token():
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            credentials = service_account.Credentials.from_service_account_file(
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        else:
            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])

        credentials.refresh(Request())
        return credentials.token

    try:
        project_id = 'auditpulse'  
        region = 'us-central1'       
        job_name = 'auditpulse-app'  
        image = "us-east1-docker.pkg.dev/auditpulse/auditpulse-images/auditpulse-app:latest"
        job_url = f"https://{region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{project_id}/jobs/{job_name}"

        mysql_conn = mysql.connector.connect(
        host='34.46.191.121',
        port=3306,
        user='root',
        database='auditpulse',
        password=os.getenv('MYSQL_GCP_PASS')
    )

        mysql_cursor = mysql_conn.cursor()

        query = """
        SELECT COUNT(*) FROM runs 
        WHERE status='queued'
        """
        mysql_cursor.execute(query)
        result = mysql_cursor.fetchone()

        count = result[0]

        if count==0:
            return {
                    'success': False,
                    'message': 'There are no jobs queued. Skipping job deployment.'
                }, 200
        per_request_time_est = 15*60
        per_instance_request = 2
        threshold = 0.25
        max_time_allowed = 6*60*60
        batches = (count + per_instance_request - 1) // per_instance_request
        total_time_est = batches * per_request_time_est
        total_time_est*=1+threshold
        total_time_est = int(total_time_est)
        total_time_est = min(total_time_est, max_time_allowed)


        token = get_auth_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        container_config = {
            "image": image,
        }
        job_config = {
            "apiVersion": "run.googleapis.com/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name
            },
            "spec": {
                "template": {
                    "metadata": {},
                    "spec": {
                        "taskCount": 1,
                        "template": {
                            "spec": {
                                "containers": [{
                                    "image": image,
                                    "resources": {
                                        "limits": {
                                            "cpu": "4000m",
                                            "memory": "2Gi"
                                        }
                                    },
                                    "env": [
                                        {
                                            "name": "SERPER_API_KEY",
                                            "valueFrom": {
                                                "secretKeyRef": {
                                                    "name": "SERPER_API_KEY",
                                                    "key": "latest"
                                                }
                                            }
                                        },
                                        {
                                            "name": "AGENTOPS_API_KEY",
                                            "valueFrom": {
                                                "secretKeyRef": {
                                                    "name": "AGENTOPS_API_KEY",
                                                    "key": "latest"
                                                }
                                            }
                                        },
                                        {
                                            "name": "MYSQL_GCP_PASS",
                                            "valueFrom": {
                                                "secretKeyRef": {
                                                    "name": "MYSQL_GCP_PASS",
                                                    "key": "latest"
                                                }
                                            }
                                        }
                                    ]
                                }],
                                "serviceAccountName": "853525367358-compute@developer.gserviceaccount.com",
                                "timeoutSeconds": total_time_est,
                                "maxRetries": 1
                            }
                        }
                    }
                }
            }
        }

        response = requests.get(job_url, headers=headers)
        if response.status_code == 404:
            # Job doesn't exist, create it
            create_response = requests.post(
                f'https://{region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{project_id}/jobs',
                headers=headers,
                json=job_config
            )
            if create_response.status_code not in [200, 201]:
                return {
                    'success': False,
                    'message': f'Failed to create job: {create_response.text}'
                }, 500
        else:
            # Job exists, update it
            update_response = requests.put(
                job_url,
                headers=headers,
                json=job_config
            )
            if update_response.status_code not in [200, 201]:
                return {
                    'success': False,
                    'message': f'Failed to update job: {update_response.text}'
                }, 500
        run_response = requests.post(
            f'{job_url}:run',
            headers=headers,
            json={}
        )
        if run_response.status_code not in [200, 201]:
            return {
                'success': False,
                'message': f'Failed to execute job: {run_response.text}'
            }, 500
        status_code =200
        status = True
        details = f'Successfully deployed the job for {total_time_est//60} minutes.'
    except Exception as e:
        status =  False
        details = str(e)
        status_code = 500
    return {'success':status, 'message':details}, status_code