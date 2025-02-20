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