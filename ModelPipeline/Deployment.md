# Model Deployment

## [View Demo](https://drive.google.com/file/d/1Co8ciP_zWOeF-XSAVvqsa9AaNy42sJRD/view?usp=sharing)

## Cloud Deployment
- **Deployment Provider**: Google Cloud Platform.
- **Model Provider**: Google Cloud Platform.
- **Deployment Service**: 
  - Google Cloud Scheduler - HTTP POST request to cloud function.
  - Google Cloud Function - HTTP POST request to Cloud Run API.
  - Google Cloud Run:
    - Service: Frontend (Streamlit) - HTTP GET request.
    - Job: Backend - Launched by Cloud Function.

## Deployment Automation
### Development:
- Code development happens locally. Once completed, it is pushed to GitHub.
- GitHub Actions workflow file triggers on push, completing the tests, pushing the built image to the Artifact Registry. An email alert notifying of the new deployment is also sent to the configured emails.
- Google Cloud Scheduler triggers a Cloud Function every 6 hours that submits a Cloud Run job with the latest pushed image. 
- The requests made in the interval are processed and stored in the bucket to be provided to the users.
- Ideally, we would have separate pages for each user run where the users can access and provide feedback on those runs, however, since this would be frontend-heavy, we prioritized other aspects of our product.

**Connection to Repository**: [auditpulse_app_workflow.yml](https://github.com/hakeematyab/AuditPulse/blob/master/.github/workflows/auditpulse_app_workflow.yml)

## Detailed Steps for Replication:
1. Clone the repository: [AuditPulse](https://github.com/hakeematyab/AuditPulse)
2. Follow the steps outlined in the [readme file](https://github.com/hakeematyab/AuditPulse/blob/master/ModelPipeline/Backend/README.md)
3. Once the environment is set up with dependencies installed, several environment variables need to be configured:
   - Google Application Credentials
   - Google API Key.
   - Serper API Key.
   - Agentops API Key.
   - MySQL GCP Password.
4. Once these API's are configured, the backend can be run through: [app.py](https://github.com/hakeematyab/AuditPulse/blob/master/ModelPipeline/Backend/src/app.py) can be run, and the reports can be generated locally for the requests sent.
5. The frontend can be accessed through the following endpoint: [auditpulse-ui](https://auditpulse-ui-853525367358.us-central1.run.app)
6. With the backend running and frontend accessible, requests to generate the audit reports.
7. For a cloud deployment, once changes are made and pushed to the repository, an image will be built and pushed to GCP.
8. Cloud scheduler will trigger batch processing every six hours with the latest image.

## Model Monitoring and Triggering Retraining
### Monitoring and Retraining: 
- Evaluation jobs are scheduled every night to compute the metrics for the generated reports.
- If 50% of the reports that day fall below 60% similarity metric threshold, a prompt refinement job would be triggered. This job would iteratively refine the prompt based on the metrics and feedback received for the said runs.
- **Retraining**: [AutoPromptRefinement](https://github.com/hakeematyab/AuditPulse/tree/master/ModelPipeline/AutoPromptRefinement)
- **Evaluation**: [Evaluation](https://github.com/hakeematyab/AuditPulse/tree/master/DataPipeline/Evaluation)
- **Notifications for Model Retraining**:
  - Email notifications are set up through the GCP monitoring service to alert configured persons in case of retraining.
- **Logging**:
  - Logs for each run are stored in the bucket with the necessary identified for traceability.