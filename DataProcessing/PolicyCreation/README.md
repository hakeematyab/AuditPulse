## Instructions

### Git Instructions
1. Branch everytime you're making changes.
    ```
    git checkout -b mybranch
    git branch --set-upstream-to=origin/mybranch
    ```
2. Update requirements file.
    ```
    cd mydir
    pip freeze > requirements.txt
    conda env export > environment.yml
    ```
3. Commit & push.
    ```
    git add file
    git commit -m "Commit message"
    git push
    ```
### DVC-GCP Setup
1. Install gcloud CLI.
2. Install and initialize dvc.
    ```
    pip install dvc
    pip install dvc-gs
    dvc init
    ```
3. Add gcp bucket:
    ```
    gcloud auth application-default login
    dvc import-url gs://auditpulse-data Data
    ```
4. Check if there are any changes:
    ```
    dvc update Data.dvc
    ```

### Docker Commands
1. Start docker engine & build image
    ```
    docker build -t policy_creation .
    ```
2. Start container with environment variables
    ```
    docker run \
    -v ~/gcp-keys/my-gcp-key.json:/app/gcp-key.json \
    --env GROQ_API_KEY="your_groq_api_key" \
    --env GOOGLE_APPLICATION_CREDENTIALS="/app/gcp-key.json" \
    --name my_container my_image
    ```