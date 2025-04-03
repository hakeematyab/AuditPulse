from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
import shutil
from datetime import datetime
import subprocess
import PyPDF2
import openai
import numpy as np
from transformers import T5Tokenizer, T5ForConditionalGeneration, AutoTokenizer, AutoModel
import torch
from transformers import RobertaTokenizer, RobertaModel, AutoModelForMaskedLM
from google.cloud import firestore, storage

os.environ["TOKENIZERS_PARALLELISM"] = "false"




def clear_temp_folder(folder_path="temp"):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove file or symbolic link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory and contents
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
        print(f"Folder '{folder_path}' has been cleared.")
    else:
        print(f"Folder '{folder_path}' does not exist.")


def documents_download(path1, path2):
    print("Starting document collection process...")

    # Temporary directory
    temp_dir = "./temp/"
    os.makedirs(temp_dir, exist_ok=True)

    # GCP Bucket details
    gcp_bucket_name = "auditpulse-data"

    # Define the two main folders
    doc1_folder = path1
    doc2_folder = path2
    print(doc1_folder)
    print(doc2_folder)

    # Download files
    doc1_files = download_all_files_from_gcp(gcp_bucket_name, doc1_folder, temp_dir)
    doc2_files = download_all_files_from_gcp(gcp_bucket_name, doc2_folder, temp_dir)

    print("Files downloaded:\nDoc1:", doc1_files, "\nDoc2:", doc2_files)

    # Process Doc1 files into input.txt
    input_text_path = os.path.join(temp_dir, "input.txt")
    with open(input_text_path, 'w', encoding='utf-8') as f:
        f.write(extract_text_from_files(doc1_files))
    print(f"Saved extracted text from Doc1 to {input_text_path}")

    # Process Doc2 files into generated.txt
    generated_text_path = os.path.join(temp_dir, "generated.txt")
    with open(generated_text_path, 'w', encoding='utf-8') as f:
        f.write(extract_text_from_files(doc2_files))
    print(f"Saved extracted text from Doc2 to {generated_text_path}")

    print("Document collection process completed.")


def extract_text_from_files(files):
    """Extracts and consolidates text from JSON, TXT, and PDF files."""
    text_content = ""

    for file_path in files:
        if file_path.endswith(".json"):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    json_data = json.load(f)
                    if isinstance(json_data, dict):
                        for key, value in json_data.items():
                            text_content += f"{key}: {value}\n\n"
                    elif isinstance(json_data, list):
                        for item in json_data:
                            if isinstance(item, dict):
                                for key, value in item.items():
                                    text_content += f"{key}: {value}\n\n"
                except json.JSONDecodeError:
                    text_content += f"Invalid JSON format in {file_path}\n\n"

        elif file_path.endswith(".txt"):
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content += f.read() + "\n"

        elif file_path.endswith(".pdf"):
            text_content += extract_text_from_pdf(file_path) + "\n"

    return text_content


def download_all_files_from_gcp(bucket_name, folder_name, local_folder):
    """Downloads all files from a GCP folder."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=folder_name)
    os.makedirs(local_folder, exist_ok=True)

    downloaded_files = []
    for blob in blobs:
        if not blob.name.endswith("/"):
            local_path = os.path.join(local_folder, os.path.basename(blob.name))
            blob.download_to_filename(local_path)
            downloaded_files.append(local_path)
            print(f"Downloaded {blob.name} to {local_path}")

    return downloaded_files


def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])


def evaluate_similarity(company_name, path1, path2):
    """Evaluate similarity between two files"""
    doc1_path = "./temp/input.txt"
    doc2_path = "./temp/generated.txt"
    doc1_text = read_text_file(doc1_path)
    doc2_text = read_text_file(doc2_path)
    
    if not doc1_text or not doc2_text:
        print("Skipping similarity evaluation due to missing file/files")
        return
    
    # Using OpenAI embedding -->2nd best
    # embedding1 = get_embedding(doc1_text)
    # embedding2 = get_embedding(doc2_text)
    # openai_similarity = cosine_similarity(embedding1, embedding2)
    print("openai_sim")
    openai_similarity = 99999.99999
    
    
    # Using T5 model
    print("t5_sim")
    t5_similarity_score = t5_similarity(doc1_text, doc2_text)
    # t5_similarity_score = 99999.99999
    
    
    # Using SBERT model --> 1st best
    sbert_similarity_score = sbert_similarity(doc1_text, doc2_text)
    # sbert_similarity_score = 99999.99999
    
    
    # Using RoBERTa model
    roberta_similarity_score = roberta_similarity(doc1_text, doc2_text)
    # roberta_similarity_score = 99999.99999

    # Using BERT model
    bert_similarity_score = bert_similarity(doc1_text, doc2_text)
    # bert_similarity_score = 99999.99999
    
    # Using Modern BERT model
    m_bert_similarity_score = m_bert_similarity(doc1_text, doc2_text)
    # m_bert_similarity_score = 99999.99999


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
    # save_comparison("input.txt", "generated.txt", score)
    db_client = firestore.Client(project='auditpulse')
    collection_name = 'config'
    document_name = 'run'
    policy_doc = get_document(db_client, collection_name, document_name)

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket("auditpulse-data")
        
        input_path = path1
        generated_path = path2

        blobs = bucket.list_blobs(prefix=path1)

        doc1_files=[]
        for blob in blobs:
            if not blob.name.endswith("/"):
                doc1_files.append(blob.name)

        blobs = bucket.list_blobs(prefix=path2)
        
        doc2_files=[]
        for blob in blobs:
            if not blob.name.endswith("/"):
                doc2_files.append(blob.name)


        compare_file_1 = doc1_files
        compare_file_2 = doc2_files
        latest_version = policy_doc.get('latest_dev_version')
        current_version = int(latest_version[3:]) + 1

        updated_collection = {
                            'active_dev_version': f'run{current_version}',
                            'latest_dev_version': f'run{current_version}',
                            f'development.run{current_version}': {
                                        'created_at': firestore.SERVER_TIMESTAMP,
                                        'company_name': company_name,
                                        "Compaired_files": {
                                            "company documents": compare_file_1,
                                            "generated documents": compare_file_2
                                            },
                                            "score": {
                                                "OpenAI score": score[0],
                                                "T5": score[1],
                                                "Sentence Bert": score[2],
                                                "RoBERTa": score[3],
                                                "Bert": score[4],
                                                "Modern BERT": score[5]
                                            },
                                                    }
                            }
        update_collection(db_client, collection_name, document_name, updated_collection)

    except Exception as e:
        print(e)


def read_text_file(file_name):
    """Reads a text file with the specified filename and returns its content."""
    text = ""
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            text = file.read()
    except FileNotFoundError:
        print(f"Error: The file {file_name} was not found.")
        return None
    except IOError:
        print(f"Error: Unable to read {file_name}.")
        return None
    return text


def get_document(db_client, collection_name, document_name):
    """
    Retrieves a document from the Firestore database.

    Args:
        db_client (firestore.Client): Firestore database client instance.
        collection_name (str): The name of the Firestore collection. Default is 'config'.
        document_name (str): The name of the document to retrieve. Default is 'policy'.

    Returns:
        dict: The document data if found, else returns a default policy structure.
    """
    policy_collection = db_client.collection(collection_name).document(document_name)
    policy_document = policy_collection.get()
    if policy_document.exists:
        return policy_document.to_dict()
    else:
        raise ValueError('Policy document does not exist.')


def update_collection(db_client, collection_name, document_name, updated_collection):
    """
    Updates the Firestore policy document with the new version details.

    Args:
        db_client (firestore.Client): Firestore database client instance.
        collection_name (str): The Firestore collection where the policy is stored. Default is 'config'.
        document_name (str): The name of the Firestore document to update. Default is 'policy'.
    Returns:
        None
    """
    policy_collection = db_client.collection(collection_name).document(document_name)
    policy_collection.update(updated_collection)


def t5_similarity(text1, text2):
    """Evaluate similarity using T5 model."""
    print("inside t5")
    tokenizer = T5Tokenizer.from_pretrained('google-t5/t5-small', legacy=False)
    model = T5ForConditionalGeneration.from_pretrained('google-t5/t5-small')
    
    inputs1 = tokenizer(text1, return_tensors="pt", padding=True)
    inputs2 = tokenizer(text2, return_tensors="pt", padding=True)
    
    with torch.no_grad():
        embedding1 = model.encoder(inputs1.input_ids)[0].mean(dim=1)
        embedding2 = model.encoder(inputs2.input_ids)[0].mean(dim=1)
    
    similarity_score = cosine_similarity(embedding1.numpy(), embedding2.numpy())
    return similarity_score

def chunk_text(text, tokenizer, max_length=512, stride=256):
    """Splits text into overlapping chunks."""
    tokens = tokenizer(text, return_tensors="pt", truncation=False)["input_ids"][0]
    chunks = [tokens[i: i + max_length] for i in range(0, len(tokens), stride)]
    
    # Ensure no chunk exceeds max_length
    chunks = [chunk[:max_length] for chunk in chunks]  # Truncate each chunk to max_length if necessary
    return chunks

def get_embedding_test(text, model, tokenizer, max_length=512, stride=256):
    """Computes embeddings for long texts using chunking."""
    print('start embidding')
    chunks = chunk_text(text, tokenizer, max_length, stride)
    embeddings = []
    
    with torch.no_grad():
        for chunk in chunks:
            # Convert chunk to tensor and ensure it's of the right shape
            chunk_tensor = torch.tensor(chunk).unsqueeze(0).clone().detach()  # Add batch dimension
            chunk_tensor = chunk_tensor[:, :max_length]  # Ensure it doesn't exceed max_length
            
            # Forward pass through the model
            outputs = model.encoder(chunk_tensor)
            embedding = outputs.last_hidden_state.mean(dim=1)  # Take the mean of the hidden states
            embeddings.append(embedding)


def get_embedding(text, model="text-embedding-ada-002"):
    """Gets text embeddings using OpenAI API."""
    client = openai.OpenAI()
    response = client.embeddings.create(
        input=text,
        model=model
    )
    return np.array(response.data[0].embedding)


def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    # Flatten the embeddings to 1D arrays
    vec1 = vec1.flatten()
    vec2 = vec2.flatten()
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


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


def detail_info(doc1, doc2):
    return [doc1, doc2]

if __name__ == "__main__":
    try:
        company_name = "sudo"
        path1 = "Evaluation/Doc1/"
        path2 = "Evaluation/Doc2/"
        clear_temp_folder()                                                 # refresh temp
        print('\n\n\n')
        documents_download(path1, path2)
        print('\n\n\n')
        evaluate_similarity(company_name, path1, path2)
        print('\n\n\n')
        clear_temp_folder()                                                 # refresh temp
    except:
        print("Error")
