import os
import PyPDF2
import openai
import numpy as np
from transformers import T5Tokenizer, T5ForConditionalGeneration, AutoTokenizer, AutoModel
import torch
from transformers import RobertaTokenizer, RobertaModel, AutoModelForMaskedLM
from datetime import datetime
import json

# openai.api_key = "api_key"  # Ensure API key is set
OUTPUT_DIR = "./Database/metrics/"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "comparisons.json")


def extract_text_from_pdf(pdf_path):
    """Extract text from a given PDF file."""
    text = ""
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except PyPDF2.errors.PdfReadError:
        print(f"Error: Unable to read {pdf_path}. The file might be corrupted.")
        return None
    return text

def save_text_to_file(text, filename):
    """Save extracted text to a file."""
    if text:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(text)

def get_embedding(text):
    """Get OpenAI embedding for a given text (Updated for v1.0.0+)."""
    response = openai.embeddings.create(
        model="text-embedding-ada-002", 
        input=[text]
    )
    return np.array(response.data[0].embedding)

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    # Flatten the embeddings to 1D arrays
    vec1 = vec1.flatten()
    vec2 = vec2.flatten()
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


# T5 model evaluation function
def t5_similarity(text1, text2):
    """Evaluate similarity using T5 model."""
    tokenizer = T5Tokenizer.from_pretrained('google-t5/t5-base')
    model = T5ForConditionalGeneration.from_pretrained('google-t5/t5-base')
    
    inputs1 = tokenizer(text1, return_tensors="pt", padding=True)
    inputs2 = tokenizer(text2, return_tensors="pt", padding=True)
    
    with torch.no_grad():
        embedding1 = model.encoder(inputs1.input_ids)[0].mean(dim=1)
        embedding2 = model.encoder(inputs2.input_ids)[0].mean(dim=1)
    
    similarity_score = cosine_similarity(embedding1.numpy(), embedding2.numpy())
    return similarity_score

# Sentence-BERT (SBERT) model evaluation function
def sbert_similarity(text1, text2):
    """Evaluate similarity using Sentence-BERT (SBERT)."""
    model_name = 'Muennighoff/SBERT-base-nli-v2'  # You can change the model to a different SBERT variant
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    
    inputs1 = tokenizer(text1, return_tensors="pt", truncation=True, padding=True)
    inputs2 = tokenizer(text2, return_tensors="pt", truncation=True, padding=True)
    
    with torch.no_grad():
        embedding1 = model(**inputs1).last_hidden_state.mean(dim=1)
        embedding2 = model(**inputs2).last_hidden_state.mean(dim=1)
    
    similarity_score = cosine_similarity(embedding1.numpy(), embedding2.numpy())
    return similarity_score

# BERT model eval function
def bert_similarity(text1, text2):
    """Evaluate similarity using BERT (BERT)."""
    model_name = 'google-bert/bert-base-uncased'  # You can change the model to a different SBERT variant
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    
    inputs1 = tokenizer(text1, return_tensors="pt", truncation=True, padding=True)
    inputs2 = tokenizer(text2, return_tensors="pt", truncation=True, padding=True)
    
    with torch.no_grad():
        embedding1 = model(**inputs1).last_hidden_state.mean(dim=1)
        embedding2 = model(**inputs2).last_hidden_state.mean(dim=1)
    
    similarity_score = cosine_similarity(embedding1.numpy(), embedding2.numpy())
    return similarity_score

# RoBERTa model evaluation function
def roberta_similarity(text1, text2):
    """Evaluate similarity using RoBERTa model."""
    # Load the tokenizer and model for RoBERTa
    tokenizer = RobertaTokenizer.from_pretrained('roberta-base')
    model = RobertaModel.from_pretrained('roberta-base')

    # Tokenize the input texts
    inputs1 = tokenizer(text1, return_tensors="pt", truncation=True, padding=True)
    inputs2 = tokenizer(text2, return_tensors="pt", truncation=True, padding=True)

    # Get the embeddings for the texts (mean pooling of last hidden state)
    with torch.no_grad():
        embedding1 = model(**inputs1).last_hidden_state.mean(dim=1)
        embedding2 = model(**inputs2).last_hidden_state.mean(dim=1)

    # Convert embeddings to numpy arrays for cosine similarity
    embedding1 = embedding1.numpy()
    embedding2 = embedding2.numpy()

    # Calculate cosine similarity
    similarity_score = cosine_similarity(embedding1, embedding2)
    if similarity_score.shape == (1, 1):
        return similarity_score[0][0]  # This returns the scalar value of similarity
    else:
        return similarity_score


# Modern Bert model evaluation function
def m_bert_similarity(text1, text2):
    """Evaluate similarity using Modern Bert model."""
    # Load the tokenizer and model for Modern Bert
    tokenizer = AutoTokenizer.from_pretrained('answerdotai/ModernBERT-base')
    model = AutoModel.from_pretrained('answerdotai/ModernBERT-base')

    # Tokenize the input texts
    inputs1 = tokenizer(text1, return_tensors="pt")
    inputs2 = tokenizer(text2, return_tensors="pt")

    # Get the embeddings for the texts (mean pooling of last hidden state)
    with torch.no_grad():
        embedding1 = model(**inputs1).last_hidden_state.mean(dim=1)
        embedding2 = model(**inputs2).last_hidden_state.mean(dim=1)

    # Convert embeddings to numpy arrays for cosine similarity
    embedding1 = embedding1.numpy()
    embedding2 = embedding2.numpy()

    # Calculate cosine similarity
    similarity_score = cosine_similarity(embedding1, embedding2)
    if similarity_score.shape == (1, 1):
        return similarity_score[0][0]  # This returns the scalar value of similarity
    else:
        return similarity_score

def save_comparison(compare_file_1, compare_file_2, score):
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

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
        "Compaired_files": {
            "file_1": compare_file_1,
            "file_2": compare_file_2
        },
        "score": {
            "OpenAI score": score[0],
            "T5": score[1],
            "Sentence Bert": score[2],
            "RoBERTa": score[3],
            "Bert": score[4],
            "Modern BERT": score[5]
        }
    }

    # Append and save
    data.append(new_entry)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print(f"Saved comparison #{new_id}")

def evaluate_similarity():
    """Evaluate similarity between PDFs in doc1 and doc2 folders."""
    doc1_files = [f for f in os.listdir("doc1") if f.endswith(".pdf")]
    doc2_files = [f for f in os.listdir("doc2") if f.endswith(".pdf")]
    

    if not doc1_files or not doc2_files:
        print("Ensure both doc1 and doc2 contain at least one PDF.")
        return
    
    doc1_path = os.path.join("doc1", doc1_files[0])
    doc2_path = os.path.join("doc2", doc2_files[0])
    
    doc1_text = extract_text_from_pdf(doc1_path)
    doc2_text = extract_text_from_pdf(doc2_path)
    
    if not doc1_text or not doc2_text:
        print("Skipping similarity evaluation due to unreadable PDFs.")
        return
    
    save_text_to_file(doc1_text, os.path.join("doc1", "extracted_doc1.txt"))
    save_text_to_file(doc2_text, os.path.join("doc2", "extracted_doc2.txt"))
    
    # Using OpenAI embedding -->2nd best
    embedding1 = get_embedding(doc1_text)
    embedding2 = get_embedding(doc2_text)
    openai_similarity = cosine_similarity(embedding1, embedding2)
    
    
    # Using T5 model
    t5_similarity_score = t5_similarity(doc1_text, doc2_text)
    
    
    # Using SBERT model --> 1st best
    sbert_similarity_score = sbert_similarity(doc1_text, doc2_text)
    
    
    # Using RoBERTa model
    roberta_similarity_score = roberta_similarity(doc1_text, doc2_text)

    # Using BERT model
    bert_similarity_score = bert_similarity(doc1_text, doc2_text)
    
    # Using Modern BERT model
    m_bert_similarity_score = m_bert_similarity(doc1_text, doc2_text)


    print(f"OpenAI Similarity Score: {openai_similarity:.4f}")
    print(f"T5 Similarity Score: {t5_similarity_score:.4f}")
    print(f"SBERT Similarity Score: {sbert_similarity_score:.4f}")
    print(f"RoBERTa Similarity Score: {roberta_similarity_score:.4f}")
    print(f"BERT Similarity Score: {bert_similarity_score:.4f}")
    print(f"Modern BERT Similarity Score: {m_bert_similarity_score:.4f}")
    

    score = np.array([float(openai_similarity), 
            float(t5_similarity_score), 
            float(sbert_similarity_score), 
            float(roberta_similarity_score), 
            float(bert_similarity_score), 
            float(m_bert_similarity_score)])
    save_comparison(doc1_files[0], doc2_files[0], score)
    


if __name__ == "__main__":
    evaluate_similarity()
