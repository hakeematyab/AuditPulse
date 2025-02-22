import json
import nltk
from nltk.tokenize import sent_tokenize
from transformers import pipeline
import torch
from datasets import Dataset
import os

nltk.download('punkt')
nltk.download('wordnet')
nltk.download('omw-1.4')

class Form10KProcessor:
    
    def __init__(self, input_path):

        self.input_path = input_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Load LLM for classification
        self.classifier = pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli", device=0 if torch.cuda.is_available() else -1)

    def extract_text(self, filePath) :

        with open(filePath, "r", encoding="utf-8") as file:
            text = file.read()
        
        return text

    def chunk_text(self, sentences, chunk_size=5, overlap=2):

        """Creates overlapping chunks of sentences."""
        chunks = []
        i = 0
        while i < len(sentences):
            chunk = sentences[i : i + chunk_size]
            chunks.append(" ".join(chunk))
            i += chunk_size - overlap
        return chunks


    def classify_sections(self, text, output_path):

        audit_data = {
            "business_overview": [],
            "risk_factors": [],
            "financial_statements": [],
            "mdna": []
        }

        """Classify extracted text into audit-related sections."""
        print("Classifying text into sections for " + output_path)

        sentences = sent_tokenize(text)
        chunks = self.chunk_text(sentences, 5, 2)

        labels = {
            "Business Overview": "This section describes the company's core business operations, products, markets, and competitive landscape.",
            "Risk Factors": "This section highlights potential financial, operational, and strategic risks that could impact the company's performance.",
            "Financial Statements": "This section includes key financial statements such as the income statement, balance sheet, and cash flow statement.",
            "MD&A": "This section includes management's discussion and analysis of the financial condition, performance, and future outlook of the company.",
            "Irrelevant": "This text is not relevant to an audit and should be ignored."
        }

        hypothesis_template = "This text is related to {} in a company's annual report."

        dataset = Dataset.from_dict({"text": chunks})
        results = self.classifier(
            dataset["text"],
            candidate_labels=list(labels.values()),
            hypothesis_template=hypothesis_template,
            multi_label=False
        )

        label_mapping = {v: k for k, v in labels.items()}

        for chunk, result in zip(chunks, results):
            label_description = result["labels"][0]  # Get the highest confidence label
            label = label_mapping[label_description]  # Convert back to short label

            if label == "Business Overview":
                audit_data["business_overview"].append(chunk)
            elif label == "Risk Factors":
                audit_data["risk_factors"].append(chunk)
            elif label == "Financial Statements":
                audit_data["financial_statements"].append(chunk)
            elif label == "MD&A":
                audit_data["mdna"].append(chunk)

        # Save classified sections to a JSON file
        classified_data_path = os.path.join(output_path, "audit_phases.json")
        with open(classified_data_path, "w", encoding="utf-8") as file:
            json.dump(audit_data, file, indent=4)
        

    def process(self):
        for company in os.listdir(self.input_path) :
            filePaths = os.path.join(self.input_path, company, "10-K")
            for year in os.listdir(filePaths) :

                formPath = os.path.join(filePaths, year)
                for formName in os.listdir(formPath) :
                    text = self.extract_text(os.path.join(formPath, formName))
                    self.classify_sections(text, formPath)
                    print("Processing complete. Output saved to: " + formPath)

if __name__ == "__main__":

    AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/Users/aniketgupta/airflow")
    input_path = os.path.join(AIRFLOW_HOME, "data/sec-edgar-filings")
    processor = Form10KProcessor(input_path)
    processor.process()
