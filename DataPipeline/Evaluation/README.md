
# Audit Report Similarity Evaluation Pipeline

This project evaluates the similarity of newly generated audit reports against saved embeddings using various transformer models. The similarity scores are logged into a MySQL database, and alerts are triggered for low similarity reports.

---

## Features

- Embedding generation using:
  - `Muennighoff/SBERT-base-nli-v2`
  - `google-bert/bert-base-uncased`
  - `answerdotai/ModernBERT-base`
  - `roberta-base`
- Cosine similarity computation
- Markdown to plain text conversion
- Similarity comparison with saved embeddings from GCP
- Result storage in MySQL
- Alert generation on low similarity
- Temporary folder cleanup automation

---

## Project Structure

```plaintext
.
└── DataPipeline
    └── Evaluation
        ├── Database
            └── metrics
            │   └── comparisons.json
        ├── Dockerfile
        ├── app.py
        ├── eval.py
        ├── evalution.py
        ├── requirements.txt
        ├── t5.py
        ├── temp
            └── generated.txt
        ├── templates
            ├── index.html
            ├── result.html
            └── results.html
        └── test_eval.py
```

---

## Requirements

- Python 3.7+
- Google Cloud SDK
- PyTorch
- Hugging Face Transformers
- NumPy
- Scikit-learn
- MySQL Connector

### Install dependencies

```bash
pip install torch transformers scikit-learn google-cloud-storage mysql-connector-python
```

---

## Configuration

Before running, set the following environment variables:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/gcp-key.json"
export MYSQL_GCP_PASS="your_mysql_password"
```

These are needed for:
- Google Cloud Storage authentication
- MySQL database access

---

## How to Run

Run the pipeline:

```bash
python t5.py
```

This will:
1. Clear the `temp/` folder
2. Get unevaluated report file paths from MySQL
3. Download and convert `.md` files to `.txt`
4. Generate embeddings using multiple transformer models
5. Compute cosine similarity
6. Store scores in MySQL
7. Trigger alert if similarity is below threshold

---

## 🛠Core Functions

| Function | Description |
|---------|-------------|
| `compare_embedding_with_saved(new_embedding, saved_embedding)` | Compute cosine similarity |
| `files_to_be_evaluated()` | Fetch unevaluated file paths |
| `documents_download(bucket_name, file_path)` | Download from GCP |
| `simple_md_to_txt(input_file, output_file)` | Markdown → plain text |
| `update_metrice_table(file_name, scores)` | Save scores to MySQL |
| `alert_trigger(file_name, model_scores, threshold=0.95)` | Trigger alert if needed |
| `clear_temp_folder()` | Clear temp directory |

---

## Database Tables

### `runs` Table

| Column     | Type     | Description                           |
|------------|----------|---------------------------------------|
| file_path  | TEXT     | Path of the report in GCP             |
| evaluated  | BOOLEAN  | Whether the report has been processed |

### `metrics` Table

| Column       | Type   | Description                          |
|--------------|--------|--------------------------------------|
| file_name    | TEXT   | Name of the report                   |
| model_name   | TEXT   | Transformer model used               |
| similarity   | FLOAT  | Cosine similarity (0 to 1)           |

---

## Alert System

An alert is triggered if **2 or more models** return similarity < `0.90`.

**Alert JSON format:**

```json
{
  "file_name": "report.txt",
  "low_similarity_models": ["SBERT", "ModernBERT"],
  "scores": {
    "SBERT": 0.83,
    "ModernBERT": 0.89
  }
}
```

**Alert is saved to:**

- **Bucket**: `auditpulse-alerts`
- **Folder**: `alerts/`
- **File Format**: `.json`

---

## 🧹 Temp Folder Usage

- All downloaded and converted files live temporarily in the `temp/` folder.
- It is cleared at the start and end of every run.

---
