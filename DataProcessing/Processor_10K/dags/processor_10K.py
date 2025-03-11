import os
import json
import nltk
import torch
import gc
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer, util
import numpy as np

# # Download necessary NLTK data
nltk.download('punkt')
nltk.download('punkt_tab')
# nltk.download('wordnet')
# nltk.download('omw-1.4')


class Form10KProcessor:
    def __init__(self, input_path):
        self.input_path = input_path

        # ✅ Use a lightweight sentence embedding model
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        # ✅ Define classification categories
        self.labels = {
            "Business Overview": "Describes the company's core business, operations, and competitors.",
            "Risk Factors": "Highlights potential financial, operational, and strategic risks.",
            "Financial Statements": "Includes key financial statements such as income statement, balance sheet, and cash flow statement.",
            "MD&A": "Management's discussion on financial condition, performance, and future outlook.",
            "Irrelevant": "Not relevant to an audit and should be ignored."
        }

        # ✅ Compute label embeddings in half precision (fp16) to reduce memory
        self.label_embeddings = self.model.encode(list(self.labels.values()), convert_to_tensor=True,
                                                  dtype=torch.float16)

    def extract_text(self, filePath):
        with open(filePath, "r", encoding="utf-8") as file:
            return file.read()

    def chunk_text(self, sentences, chunk_size=5, overlap=2):
        """Creates overlapping chunks of sentences."""
        chunks = []
        i = 0
        while i < len(sentences):
            chunk = sentences[i: i + chunk_size]
            chunks.append(" ".join(chunk))
            i += chunk_size - overlap
        return chunks

    def classify_sections(self, text, output_path):
        """Classify extracted text into audit-related sections using embeddings."""
        audit_data = {
            "business_overview": [],
            "risk_factors": [],
            "financial_statements": [],
            "mdna": []
        }

        print("Classifying text into sections for " + output_path)

        sentences = sent_tokenize(text)
        chunks = self.chunk_text(sentences, chunk_size=5, overlap=2)
        batch_size = 10  # ✅ Process in smaller batches to reduce memory usage

        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            chunk_embeddings = self.model.encode(batch_chunks, convert_to_tensor=True, dtype=torch.float16)

            # ✅ Compute cosine similarity between chunk embeddings and label embeddings
            similarities = util.pytorch_cos_sim(chunk_embeddings, self.label_embeddings)
            best_labels_idx = np.argmax(similarities.cpu().numpy(), axis=1)
            label_names = list(self.labels.keys())

            for chunk, label_idx in zip(batch_chunks, best_labels_idx):
                label = label_names[label_idx]

                if label == "Business Overview":
                    audit_data["business_overview"].append(chunk)
                elif label == "Risk Factors":
                    audit_data["risk_factors"].append(chunk)
                elif label == "Financial Statements":
                    audit_data["financial_statements"].append(chunk)
                elif label == "MD&A":
                    audit_data["mdna"].append(chunk)

            # ✅ Free memory after processing each batch
            torch.cuda.empty_cache()
            gc.collect()  # ✅ Trigger garbage collection

        # Save classified sections to a JSON file
        classified_data_path = os.path.join(output_path, "audit_phases.json")
        with open(classified_data_path, "w", encoding="utf-8") as file:
            json.dump(audit_data, file, indent=4)

    def process(self):
        for company in os.listdir(self.input_path):
            company_path = os.path.join(self.input_path, company)
            if os.path.isdir(company_path):
                filePaths = os.path.join(company_path, "10-K")
                if os.path.isdir(filePaths):
                    for year in os.listdir(filePaths):
                        year_path = os.path.join(filePaths, year)
                        if os.path.isdir(year_path):
                            for formName in os.listdir(year_path):
                                text = self.extract_text(os.path.join(year_path, formName))
                                self.classify_sections(text, year_path)
                                print("Processing complete. Output saved to: " + year_path)



if __name__ == "__main__":
    AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/opt/airflow")
    # AIRFLOW_HOME = os.getcwd()
    input_path = os.path.join(AIRFLOW_HOME, "data/sec-edgar-filings")
    processor = Form10KProcessor(input_path)
    processor.process()
