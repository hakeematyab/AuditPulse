import os
import json
import numpy as np
import torch
import PyPDF2
import openai
from transformers import T5Tokenizer, T5ForConditionalGeneration, AutoTokenizer, AutoModel, RobertaTokenizer, RobertaModel
from datetime import datetime
from langchain.llms import OpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool

# Ensure API key is set
# openai.api_key = ""
OUTPUT_DIR = "./Database/metrics/"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "comparisons.json")

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except PyPDF2.errors.PdfReadError:
        return None
    return text

# Compute cosine similarity
def cosine_similarity(vec1, vec2):
    vec1 = vec1.flatten()  # Ensure correct shape
    vec2 = vec2.flatten()  # Ensure correct shape
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


# Similarity functions
def t5_similarity(text1, text2):
    tokenizer = T5Tokenizer.from_pretrained('google-t5/t5-base')
    model = T5ForConditionalGeneration.from_pretrained('google-t5/t5-base')
    
    inputs1 = tokenizer(text1, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs2 = tokenizer(text2, return_tensors="pt", padding=True, truncation=True, max_length=512)

    with torch.no_grad():
        embedding1 = model.encoder(inputs1.input_ids)[0].mean(dim=1)
        embedding2 = model.encoder(inputs2.input_ids)[0].mean(dim=1)
    
    return cosine_similarity(embedding1.squeeze().numpy(), embedding2.squeeze().numpy())

def bert_similarity(text1, text2):
    tokenizer = T5Tokenizer.from_pretrained('google-bert/bert-base-uncased')
    model = T5ForConditionalGeneration.from_pretrained('google-bert/bert-base-uncased')
    
    inputs1 = tokenizer(text1, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs2 = tokenizer(text2, return_tensors="pt", padding=True, truncation=True, max_length=512)

    with torch.no_grad():
        embedding1 = model.encoder(inputs1.input_ids)[0].mean(dim=1)
        embedding2 = model.encoder(inputs2.input_ids)[0].mean(dim=1)
    
    return cosine_similarity(embedding1.squeeze().numpy(), embedding2.squeeze().numpy())

def sbert_similarity(text1, text2):
    tokenizer = AutoTokenizer.from_pretrained('Muennighoff/SBERT-base-nli-v2')
    model = AutoModel.from_pretrained('Muennighoff/SBERT-base-nli-v2')

    inputs1 = tokenizer(text1, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs2 = tokenizer(text2, return_tensors="pt", padding=True, truncation=True, max_length=512)

    with torch.no_grad():
        embedding1 = model(**inputs1).pooler_output
        embedding2 = model(**inputs2).pooler_output
    
    return cosine_similarity(embedding1.squeeze().numpy(), embedding2.squeeze().numpy())

def save_comparison(compare_file_1, compare_file_2, scores):
    # Load existing data or start fresh
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    # Determine new ID
    new_id = data[-1]["id"] + 1 if data else 1

    # Create new entry
    new_entry = {
        "id": new_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Compared_files": {
            "file_1": compare_file_1,
            "file_2": compare_file_2
        },
        "scores": {
            "T5 Similarity": scores[0],
            "SBERT Similarity": scores[1]
        }
    }

    # Append and save
    data.append(new_entry)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print(f"Saved comparison #{new_id}")


# Define the tool for document comparison
def compare_documents():
    doc1_files = [f for f in os.listdir("doc1") if f.endswith(".pdf")]
    doc2_files = [f for f in os.listdir("doc2") if f.endswith(".pdf")]
    
    if not doc1_files or not doc2_files:
        return "No PDFs found in doc1 or doc2."
    
    doc1_text = extract_text_from_pdf(os.path.join("doc1", doc1_files[0]))
    doc2_text = extract_text_from_pdf(os.path.join("doc2", doc2_files[0]))
    
    if not doc1_text or not doc2_text:
        return "Error extracting text."
    
    t5_score = float(t5_similarity(doc1_text, doc2_text))  # Convert to float
    sbert_score = float(sbert_similarity(doc1_text, doc2_text))  # Convert to float

    save_comparison(doc1_files[0], doc2_files[0], [t5_score, sbert_score])

    result = {
        "T5 Similarity": t5_score,
        "SBERT Similarity": sbert_score,
    }
    
    return json.dumps(result, indent=4)


# LangChain agent setup
llm = OpenAI(temperature=0)
memory = ConversationBufferMemory(memory_key="chat_history")
tools = [Tool(name="Document Comparator", func=lambda *args, **kwargs: compare_documents(), description="Compare two documents for similarity.")]


document_comparator_agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
    agent_kwargs={"role": "document comparator", "prompt": "You are given two documents. Check if they are similar or not."}
)

def run_comparison():
    return document_comparator_agent.run("Compare the documents in doc1 and doc2.")

if __name__ == "__main__":
    print(run_comparison())
