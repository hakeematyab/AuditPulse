# AuditPulse Model Pipeline

## Folder Structure

```
ModuleName/
├── Backend/
├── Frontend/
├── Notebooks/
└── README.md

```

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
    cd ModelPipeline
    conda env create -f environment.yml
    conda activate ModuleName
    pip install -r requirements.txt
   ```

## **Model Development**

### Loading Data from the Data Pipeline

#### Form 10-K

Load processed and versioned data seamlessly from the data pipeline. The process includes:
Calling the API to download Form 10-K filings for a list of companies from the past five years.
Classifying text into relevant phases using a text-based classification method.

Initialization:
Loads the all-MiniLM-L6-v2 sentence transformer to convert text into vector embeddings.
Defines five high-level categories: Business Overview, Risk Factors, Financial Statements, MD&A, and Irrelevant.
Embeddings for these category descriptions are pre-computed for classification.

Text Processing:
Reads the 10-K text files from a directory structure organized by company and year.
Tokenizes text into sentences, then splits them into overlapping chunks to preserve context.

Classification:
Each chunk is encoded into an embedding.
Cosine similarity is used to match each chunk to the most relevant label/category.
Relevant chunks are stored under one of four audit-relevant sections (irrelevant chunks are discarded).

Output:
The classified content is saved as a audit_phases.json file in the corresponding company's 10-K directory.
Running bias detection on the classified text.
Storing the final output in a designated bucket.

#### Compliance Policy

The compliance standards are extremely large documents. Deterministically or manually generating the enforceable compliance guidelines isn’t feasible or scalable. Therefore, we leveraged an LLM API to generate these guidelines. We currently use the Groq API; however, similar LLM API’s could be employed by swapping the respective clients. The enforcement of structured JSON output was ensured with the Pydantic module and retry mechanisms. It consists of the following keys:

- Rule ID: Reference rule identifier.
- Standard: The section under which the rule falls.
- Description: General description of the guideline.
- Enforcement Guidelines: Step by step process to enforce the guideline.

This module also integrates GCP Firestore and GCP Buckets. Most of the configurable parameters, like maximum token length, temperature, and document paths, are stored and retrieved from the GCP Firestore. Documents such as the standards file and prompts, on the other hand, are stored and retrieved from the GCP bucket. This provides us of control over the quality of outputs without the need to repeat the cycle. The entire module turned into a docker image and pushed to GCP. This image will be launched through GCP Cloud run. For a given company, this operation would be launched once per year or when the compliance standards are amended. As such, for automation, a cloud function that would monitor for changes in the active standards document would be suitable. Since this is an isolated operation without dependency on the ground truth collection and processing event and different run schedules, we decided for it not to be a part of the DAG and instead remain as an isolated job.

`If you want to reproduce the results, please reach out, as you would require the service account key to interact with our GCP project.`

### Training and Selecting the Best Model

Our application would involve largely prompt refinement based on the results of the similarity evaluation with the ground truth. After completing each experiment, we will evaluate the results. During the evaluation, an evaluation collection in the GCP database gets updated. This collection would contain all the metadata such as the metric values, prompt location, etc. In addition, we would also update the collection to point to the model with the best performance. In operation, the application would pick the prompts and the parameters of the best-performing experiment. We also plan to have a trigger that would launch another container if there was a change in the best-performing model and direct a small amount of traffic there.

### Model Validation

Model validation is performed using cosine similarity to compare two documents: one generated by the model and another being the official 10-K form released by the company. The model-generated document consists of multiple JSON files, which are first converted into text. Both documents are then embedded using five different models—OpenAI, T5-small, BERT, RoBERTa, and Modern BERT—to generate similarity scores. These scores are stored in Firestore, which is ideal for development due to its real-time retrieval and model correction capabilities. Upon completion of development, the data will be migrated to BigQuery for scalable storage and analysis. The model is designed to handle diverse inputs and merge them into a unified document for validation.

### Model Bias Detection (Using Slicing Techniques)
In the AuditPulse project, TensorFlow Model Analysis (TFMA) and sector-based data slicing were used to detect model bias. The dataset was segmented by industry sectors like technology, finance, and healthcare, allowing performance comparison across groups. TFMA evaluated fairness metrics, including equal opportunity and demographic parity, identifying any disparities. Accuracy, precision, recall, and F1-scores were analyzed to detect inconsistencies.
Threshold analysis was conducted to assess the impact of prediction thresholds on fairness, ensuring an optimal balance between performance and equity. Feature importance was examined to determine whether specific variables disproportionately influenced predictions for certain sectors.


### Code to Check for Bias
The bias detection framework in AuditPulse was implemented with a structured approach across the ML pipeline. A data preprocessing pipeline cleaned and balanced the dataset, addressing underrepresentation and missing data biases. A model training wrapper was integrated with fairness constraints using Fairlearn, ensuring unbiased learning.
Using AI Fairness 360, methods like equalized odds post-processing and reject option classification were implemented to adjust predictions, ensuring no sector was unfairly advantaged or disadvantaged. Additionally, feature importance analysis helped identify variables contributing to bias, allowing targeted adjustments in model inputs.


### Pushing the Model to Artifact or Model Registry

All the experiments will have their associated prompts and metadata stored on the database and GCP bucket. The database will not only serve as a versioning system but it will also contain the pointers to the best-performing configuration.

### Hyperparameter Tuning
Most of the conventional hyperparameter tuning approaches and parameters don’t completely apply to our application since it is a Websearch + RAG type of application. However, we log all the experiments and their evaluation results allowing us to perform better experiments after each trial.

### Experiment Tracking and Results

#### Tracking Tools

To track model development experiments, Firestore is used during the development phase due to its real-time retrieval and flexibility in updating similarity scores. Each experiment logs the model used (OpenAI, T5-small, BERT, RoBERTa, Modern BERT), cosine similarity scores, and document versions. Once development is complete, the data will be migrated to BigQuery for scalable storage and further analysis. Additionally, MLflow can be integrated to track model parameters, embeddings, and performance metrics, ensuring a structured approach to model improvement.

#### Results and Model Selection

The validation results are stored in JSON format, comparing the model-generated document with the official 10-K form using cosine similarity. A bar plot visualization is used to compare similarity scores across different embedding models, highlighting performance variations. The final model selection is based on the highest average cosine similarity across multiple test cases, ensuring the most accurate document embedding approach is chosen.

#### Model Sensitivity Analysis
Once again since our application is Websearch + RAG type of application, we can’t vary the features and have a valid comparison. However, we log all the experiments and their evaluation results allowing us to perform better experiments after each trial.

### Model Bias Detection (Using Slicing Techniques)

To ensure fairness in AuditPulse, the dataset was broken down into meaningful slices, including industry sectors, allowing a detailed analysis of model performance across different subgroups. Using Fairlearn, we evaluated model predictions for each slice to detect any disparities.

Key metrics such as accuracy and F1-score were tracked across these slices to quantify performance differences. AI Fairness 360 (AIF360) was used to compute fairness metrics, including demographic parity, equal opportunity, and disparate impact, helping to identify whether the model exhibited favoritism toward any specific group. Additionally, SHAP values were analyzed to understand feature importance, revealing if certain attributes disproportionately influenced predictions. The What-If Tool provided an interactive view of model behavior, visualizing how changes in input features affected different subgroups.

When bias was detected, multiple mitigation strategies were applied. Resampling techniques balanced underrepresented groups, and re-weighting methods ensured fairer distributions. Fairness constraints were integrated into model training to optimize both accuracy and equity, while post-processing techniques like reject option classification and equalized odds adjustments refined predictions to reduce disparities.

The mitigation process includes techniques used to reduce or correct detected biases in the model’s predictions. This was done through a bias mitigation module that applied post-processing techniques, specifically:
Equalized Odds Post-Processing – Adjusted predictions to ensure that model outcomes were equally likely across different sector groups while maintaining accuracy. This method modified decision thresholds to balance true positive and false positive rates across sectors.

Reject Option Classification – Adjusted decisions in uncertain cases by favoring outcomes that reduce disparities. This ensured that for borderline predictions, preference was given to fairness-improving decisions.

These techniques were implemented using AI Fairness 360, ensuring that fairness constraints were met without significantly compromising model performance. The mitigation module was integrated into the pipeline so that identified biases could be corrected dynamically, ensuring consistent fairness across financial sectors.
All mitigation steps were thoroughly documented, detailing the methods used, trade-offs considered, and justifications for each corrective action. This transparent approach ensures accountability and continuous fairness monitoring, with automated alerts flagging any significant deviations in fairness metrics over time.

### CI/CD Pipeline Automation for Model Development

#### CI/CD Setup for Model Training:
The training equivalent in our application is prompt refinement. This is a script that is triggered when a certain number of runs fall below a certain threshold. Utilizing the feedback and similarity scores, we refine and auto-tune the prompt using an LLM that is, modify the prompt and evaluate the similarity score. For now, the exit criteria is a set number of iterations but ideally, it would be until we reach a predetermined threshold for the similarity score. Each evaluation will have an entry in the Firestore database which will update the prompt that yielded the highest metric.

#### Automated Model Validation
At each submission and update to the code, the pipeline automatically validates the trained model by evaluating its performance on the validation set and generating metrics. If the validation passes a predefined threshold, the model proceeds to the next step.

#### Validation Metrics:
Evaluate the trained model on a hold-out validation dataset using metrics such as accuracy, precision, recall, F1-score, or cosine similarity depending on the task.
Store validation results in a structured format (e.g., JSON) for further analysis.

#### Threshold-Based Validation
Define a performance threshold (e.g., average cosine similarity ≥ 0.90). If the model meets this threshold, proceed to the next step; otherwise, trigger alerts for investigation.

#### Automated Model Bias Detection

The pipeline should also include steps to perform bias detection across different data slices. Results from these checks should be logged, and any significant bias should trigger an alert or block the deployment.

If bias is detected, the system triggers the appropriate bias mitigation techniques such as re-sampling, re-weighting, and adjusting decision thresholds based on the specific slice showing bias. The mitigation process is automated and executed without manual intervention, ensuring that the model is adjusted before redeployment. If the system detects significant bias that exceeds predefined thresholds, it can automatically block deployment. This prevents biased models from being deployed to production. This control is integrated into the CI/CD pipeline, ensuring that only models meeting fairness requirements are released. The system is continuously monitoring the model’s performance and fairness metrics as new data is ingested. If there is any drift in bias or fairness metrics over time, the pipeline will send an alert or trigger a re-assessment, ensuring the model remains unbiased during its operational life cycle.

#### Model Deployment or Registry Push
All the experiments will have their associated prompts and metadata stored on the database and GCP bucket. The database will not only serve as a versioning system but it will also contain the pointers to the best-performing configuration.
Notifications and Alerts
To ensure continuous monitoring of model performance, an automated notification system is implemented. If the average cosine similarity score across all models falls below a predefined threshold (T = 0.90), an email alert is triggered. This notification informs the development team of potential validation failures, prompting further investigation and necessary model adjustments. The alert system ensures proactive handling of inconsistencies, enabling timely improvements to enhance the model’s accuracy and reliability.

#### Rollback Mechanism
Our application would involve largely prompt refinement based on the results of the similarity evaluation with the ground truth. After completing each experiment, we will evaluate the results. During the evaluation, an evaluation collection in the GCP database gets updated. This collection would contain all the metadata such as the metric values, prompt location, etc. In addition, we would also update the collection to point to the model with the best performance. In operation, the application would pick the prompts and the parameters of the best-performing experiment. We also plan to have a trigger that would launch another container if there was a change in the best-performing model and direct a small amount of traffic there. 
Since we would only be directing a small amount of traffic to the newly initialized container with a modified configuration, if the results are subpar, we would still be able to gather valuable feedback about the configuration. If the same configuration surpasses a predetermined threshold repeatedly, it would trigger a cloud function or internal mechanism to terminate the container and initiate a prompt refinement script. Ideally, the prompt refinement script, with the feedback available, would improve the prompt and hence the performance of the configuration.