import pdfplumber
import json
import nltk
import argparse
from nltk.tokenize import sent_tokenize
from transformers import pipeline
import torch
from datasets import Dataset
import os

nltk.download('punkt')
nltk.download('wordnet')
nltk.download('omw-1.4')

class Form10KProcessor:
    
    def __init__(self, pdf_path, output_path):
        self.pdf_path = pdf_path
        self.output_path = output_path
        os.makedirs(output_path, exist_ok=True)  # Ensure output directory exists
        self.text = ""
        self.audit_data = {
            "business_overview": [],
            "risk_factors": [],
            "financial_statements": [],
            "mdna": []
        }
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Load LLM for classification
        self.classifier = pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli", device=0 if torch.cuda.is_available() else -1)

    def extract_text(self) :
        with open("MSFT_10K.txt", "r", encoding="utf-8") as file:
            text = file.read()
        
        self.text = text
        extracted_text_path = os.path.join(self.output_path, "extracted_text.txt")
        with open(extracted_text_path, "w", encoding="utf-8") as file:
            file.write(self.text)
            
        return text


    def extract_text_pdf(self):
        """Extract text from the uploaded PDF and save it."""
        print("Extracting text from PDF...")
        text = ""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text + "\n"
        self.text = text
        
        # Save extracted text to a file
        extracted_text_path = os.path.join(self.output_path, "extracted_text.txt")
        with open(extracted_text_path, "w", encoding="utf-8") as file:
            file.write(self.text)
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

    def classify_sections(self):
        """Classify extracted text into audit-related sections."""
        print("Classifying text into sections...")

        sentences = sent_tokenize(self.text)
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
                self.audit_data["business_overview"].append(chunk)
            elif label == "Risk Factors":
                self.audit_data["risk_factors"].append(chunk)
            elif label == "Financial Statements":
                self.audit_data["financial_statements"].append(chunk)
            elif label == "MD&A":
                self.audit_data["mdna"].append(chunk)

        # Save classified sections to a JSON file
        classified_data_path = os.path.join(self.output_path, "classified_sections.json")
        with open(classified_data_path, "w", encoding="utf-8") as file:
            json.dump(self.audit_data, file, indent=4)
        
        return self.audit_data

    def map_to_audit_phases(self):
        """Categorize extracted data into different audit phases and save the result."""
        audit_phases = {
            "Planning Phase": [self.audit_data["business_overview"], self.audit_data["risk_factors"]],
            "Risk Assessment": [self.audit_data["mdna"]],
            "Substantive Testing": [self.audit_data["financial_statements"]],
            "Completion & Reporting": [self.audit_data["mdna"]]
        }

        # Save audit phases to a JSON file
        audit_phases_path = os.path.join(self.output_path, "audit_phases.json")
        with open(audit_phases_path, "w", encoding="utf-8") as file:
            json.dump(audit_phases, file, indent=4)
        
        return audit_phases

    def process(self):
        """Run the full pipeline and save all outputs."""
        self.extract_text()
        self.classify_sections()
        audit_data = self.map_to_audit_phases()
        print("Processing complete. Output saved to:", self.output_path)
        return audit_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a Form 10-K PDF and extract audit-related information.")
    parser.add_argument("input_path", type=str, help="Path to the input PDF file")
    parser.add_argument("output_path", type=str, help="Directory to save output JSON files")
    args = parser.parse_args()

    processor = Form10KProcessor(args.input_path, args.output_path)
    processor.process()
