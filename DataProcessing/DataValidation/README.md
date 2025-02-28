## Prerequisites

1. **Anaconda**: [Download and install Anaconda](https://www.anaconda.com/download).  
   - After installation, verify it by running:
     ```bash
     conda --version
     ```

2. **Python 3.x**: [Download and install Python](https://www.python.org/downloads/) (if not already included with Anaconda).  
   - Verify the installation by running:
     ```bash
     python --version
     ```

3. **Git**: [Download and install Git](https://git-scm.com/downloads).  
   - Confirm installation by running:
     ```bash
     git --version
     ```

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/hakeematyab/AuditPulse.git
   cd AuditPulse
   ```
2. Create an environment & install dependencies
   ```sh
    cd DataProcessing/DataValidation
    conda env create -f environment.yml
    conda activate DataValidation
    pip install -r requirements.txt
   ```
## Folder Structure

Data validation will be part of the core application. As such logging and tests will be done in that pipeline.

```
DataValidation/
├── data_validation.py
├── requirements.txt
├── environment.yml
└── README.md

```
## Development Instructions

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