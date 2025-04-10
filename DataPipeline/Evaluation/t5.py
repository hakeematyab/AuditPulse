import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoTokenizer, AutoModel
from google.cloud import storage
import tempfile
import os
import mysql.connector

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
    chunk_char_size=1000):
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


def files_to_be_evaluated():
    # Step 1: Database connection config
    mysql_conn = mysql.connector.connect(
        host='34.46.191.121',
        port=3306,
        user='root',
        database='auditpulse',
        password=os.getenv('MYSQL_GCP_PASS')
    )

    mysql_cursor = mysql_conn.cursor()

    query = """
    SELECT run_id, audit_report_path
    FROM runs
    WHERE evaluation_status = 0 AND audit_report_path IS NOT NULL;
    """

    mysql_cursor.execute(query)
    id_and_paths = mysql_cursor.fetchall()  # Use fetchall() to get the result
    path=[]
    run_id=[]
    for id_and_path in id_and_paths:
        print(id_and_path)
        path.append(id_and_path[1])
        run_id.append(id_and_path[0])

    # No need to commit after a SELECT query
    mysql_cursor.close()
    mysql_conn.close()
    return [path, run_id]

def download_specific_files_from_gcp(bucket_name, folder_name, local_folder, file_paths):
    """Downloads specific files from a GCP folder based on full file paths."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=folder_name)
    os.makedirs(local_folder, exist_ok=True)

    downloaded_files = []
    for blob in blobs:
        if not blob.name.endswith("/"):
            # Check if the blob's full path matches any of the provided file paths
            if blob.name in file_paths:
                local_path = os.path.join(local_folder, os.path.basename(blob.name))
                blob.download_to_filename(local_path)
                downloaded_files.append(local_path)

    return downloaded_files

def documents_download(path1, file_paths):
    # Temporary directory
    temp_dir = "./temp/"
    os.makedirs(temp_dir, exist_ok=True)

    # GCP Bucket details
    gcp_bucket_name = "auditpulse-data"

    # Define the folder to look in
    doc1_folder = path1
    # print(f"Searching in folder: {doc1_folder}")

    # Download specific files
    doc1_files = download_specific_files_from_gcp(gcp_bucket_name, doc1_folder, temp_dir, file_paths)

    # print("Files downloaded:", doc1_files)
    return doc1_files

def simple_md_to_txt(md_path, txt_path):
    with open(md_path, 'r', encoding='utf-8') as md_file:
        lines = md_file.readlines()

    cleaned_lines = []
    for line in lines:
        # Strip basic markdown symbols
        line = line.strip()
        line = line.replace('#', '')
        line = line.replace('*', '')
        line = line.replace('-', '')
        line = line.replace('`', '')
        cleaned_lines.append(line.strip())

    with open(txt_path, 'w', encoding='utf-8') as txt_file:
        txt_file.write('\n'.join(cleaned_lines))


def update_metrice_table(file_path, sbert_score, mbert_score, bert_score, roberta_score, run_id, path):
    # Step 1: Database connection config
    mysql_conn = mysql.connector.connect(
        host='34.46.191.121',
        port=3306,
        user='root',
        database='auditpulse',
        password=os.getenv('MYSQL_GCP_PASS')
    )

    mysql_cursor = mysql_conn.cursor()

    # Step 2: Insert into the metrics table
    insert_query = """
    INSERT INTO metrics (gen_report, sbert_score, mbert_score, bert_score, roberta_score, run_id, prompt_path)
    VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    mysql_cursor.execute(insert_query, (file_path, sbert_score, mbert_score, bert_score, roberta_score, run_id, path))

    # Step 3: Update the runs table
    update_query = """
    UPDATE runs
    SET evaluation_status = 1
    WHERE run_id = %s;
    """
    mysql_cursor.execute(update_query, (run_id,))  # run_id is used for updating the evaluation_status
    
    # Commit the changes to the database
    mysql_conn.commit()

    # Step 4: Close the cursor and connection
    mysql_cursor.close()
    mysql_conn.close()

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


if __name__ == "__main__":
    
    # clear temp
    clear_temp_folder("./temp")

    # extract file names from sql
    files = files_to_be_evaluated()
    file_paths_to_evaluate = files[0]
    run_id = files[1]

    #download the files
    local_path = documents_download("generated_reports/audit_report", file_paths_to_evaluate)

    #check if any file is left to evaluate or not
    if not local_path:
        print('No new files to evaluate')

        # clear temp
        clear_temp_folder("./temp")

    else:
        for index, file in enumerate(local_path):

            # convert md to txt
            simple_md_to_txt(file, './temp/generated.txt')

            # evaluate similirity score
            sbert_score = compare_sbert_with_saved("./temp/generated.txt")
            mbert_score = compare_modernbert_with_saved("./temp/generated.txt")
            bert_score = compare_bert_with_saved("./temp/generated.txt")
            roberta_score = compare_roberta_with_saved("./temp/generated.txt")
            print(type(sbert_score))
            print(type(float(sbert_score)))

            print("File that is evaluated now:")
            print(f"{index+1}: ",file_paths_to_evaluate[index])    
            print("run_id:")
            print(f"{index+1}: ", run_id[index])
            update_metrice_table(file_paths_to_evaluate[index], float(sbert_score), float(mbert_score), float(bert_score), float(roberta_score), run_id[index], "sudo/path")
        # clear temp
        clear_temp_folder("./temp")
    

