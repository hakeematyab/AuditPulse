import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoTokenizer, AutoModel
from google.cloud import storage
import tempfile
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

def cosine_similarity_custom(vector1, vector2):
    """
    Compute cosine similarity between two vectors from scratch.
    
    Args:
        vector1 (numpy.array): The first vector.
        vector2 (numpy.array): The second vector.
    
    Returns:
        float: The cosine similarity between the two vectors.
    """
    # Ensure both vectors are numpy arrays
    vector1 = np.asarray(vector1)
    vector2 = np.asarray(vector2)
    
    # Compute dot product
    dot_product = np.dot(vector1, vector2)
    
    # Compute the magnitudes (norms) of the vectors
    norm1 = np.linalg.norm(vector1)
    norm2 = np.linalg.norm(vector2)
    
    # Calculate cosine similarity
    similarity = dot_product / (norm1 * norm2)
    
    return similarity

def compare_embedding_with_saved(
    new_file_path,
    model_name,
    gcp_bucket,
    gcs_embedding_path,
    chunk_char_size=1000
):
    # Load model & tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()

    # Load saved embedding from GCS
    client = storage.Client()
    bucket = client.bucket(gcp_bucket)
    blob = bucket.blob(gcs_embedding_path)
    with tempfile.NamedTemporaryFile(suffix=".npy") as temp_file:
        blob.download_to_filename(temp_file.name)
        saved_embedding = np.load(temp_file.name)

    # Generate embedding for the new file
    embedding_sum = None
    chunk_count = 0
    with open(new_file_path, 'r', encoding='utf-8') as f:
        buffer = ""
        for line in f:
            buffer += line
            if len(buffer) >= chunk_char_size:
                inputs = tokenizer(buffer, return_tensors="pt", truncation=True, padding=True, max_length=512)
                with torch.no_grad():
                    embedding = model(**inputs).last_hidden_state.mean(dim=1).squeeze()
                embedding_sum = embedding if embedding_sum is None else embedding_sum + embedding
                chunk_count += 1
                buffer = ""
        if buffer:
            inputs = tokenizer(buffer, return_tensors="pt", truncation=True, padding=True, max_length=512)
            with torch.no_grad():
                embedding = model(**inputs).last_hidden_state.mean(dim=1).squeeze()
            embedding_sum = embedding if embedding_sum is None else embedding_sum + embedding
            chunk_count += 1

    new_embedding = (embedding_sum / chunk_count).numpy()

    # Compare embeddings
    similarity = cosine_similarity(
        new_embedding.reshape(1, -1),
        saved_embedding.reshape(1, -1)
    )[0][0]

    print(f"✅ Cosine Similarity: {similarity:.4f}")
    return similarity

def compare_sbert_with_saved(new_file_path, gcp_bucket="auditpulse-data", gcs_embedding_path="Evaluation/Doc3/sbert_embd-large.npy"):
    return compare_embedding_with_saved(
        new_file_path=new_file_path,
        model_name="Muennighoff/SBERT-base-nli-v2",
        gcp_bucket=gcp_bucket,
        gcs_embedding_path=gcs_embedding_path
    )

def compare_bert_with_saved(new_file_path, gcp_bucket="auditpulse-data", gcs_embedding_path="Evaluation/Doc3/bert_embd-large.npy"):
    return compare_embedding_with_saved(
        new_file_path=new_file_path,
        model_name='google-bert/bert-base-uncased',
        gcp_bucket=gcp_bucket,
        gcs_embedding_path=gcs_embedding_path
    )

def compare_modernbert_with_saved(new_file_path, gcp_bucket="auditpulse-data", gcs_embedding_path="Evaluation/Doc3/modernbert_embd-large.npy"):
    return compare_embedding_with_saved(
        new_file_path=new_file_path,
        model_name='answerdotai/ModernBERT-base',
        gcp_bucket=gcp_bucket,
        gcs_embedding_path=gcs_embedding_path
    )

def compare_roberta_with_saved(new_file_path, gcp_bucket="auditpulse-data", gcs_embedding_path="Evaluation/Doc3/roberta_embd-large.npy"):
    return compare_embedding_with_saved(
        new_file_path=new_file_path,
        model_name='roberta-base',
        gcp_bucket=gcp_bucket,
        gcs_embedding_path=gcs_embedding_path
    )

if __name__ == "__main__":
    sbert_score = compare_sbert_with_saved("./temp/generated.txt")
    mbert_score = compare_modernbert_with_saved("./temp/generated.txt")
    bert_score = compare_bert_with_saved("./temp/generated.txt")
    roberta_score = compare_roberta_with_saved("./temp/generated.txt")
    print(sbert_score)
    print(mbert_score)
    print(bert_score)
    print(roberta_score)
    

