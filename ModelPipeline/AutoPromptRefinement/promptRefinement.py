import os
import yaml
import logging
from datetime import datetime
import mysql.connector
from google.cloud import storage
from google.cloud import firestore
from crewai import Agent, Task, Crew
from crewai.llm import LLM
import re
from types import MappingProxyType
import collections.abc

# ---------------- CONFIG ----------------
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'auditpulse-9aaddcc95ee9.json'
GCS_BUCKET_NAME = "auditpulse-data"
SUBFOLDERS = [
    "audit_planning",
    "client_acceptance",
    "evaluation_reporting",
    "testing_evidence_gathering"
]
LOG_FILE = f"refine_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

llm = LLM(
    model="vertex_ai/gemini-2.0-flash-lite-001",
    max_tokens=	4096,
    context_window_size=950000,
)

# ----------------------------------------


# ---------------- LOGGING ----------------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)
# -----------------------------------------


# ---------------- SQL SETUP ----------------
db = mysql.connector.connect(
    host='34.46.191.121',
    port=3306,
    user='root',
    database='auditpulse',
    # password=os.getenv("MYSQL_GCP_PASS")
    password='.}F,BOs)v=Ca@2|T'
)
cursor = db.cursor(dictionary=True)

def get_completed_runs_with_prompt_path():
    cursor.execute("""
        SELECT run_id, prompt_path
        FROM runs
        WHERE status = 'completed' AND prompt_path IS NOT NULL AND prompt_path <> '';
    """)
    return cursor.fetchall()

def update_prompt_path_to_v1(run_id, new_path):
    cursor.execute("UPDATE runs SET prompt_path = %s WHERE run_id = %s", (new_path, run_id))
    db.commit()
# -------------------------------------------

def get_next_version_path(prompt_path: str) -> str:
    """
    Given a prompt path ending in /v(num), returns the same path but with v(num+1).
    """
    match = re.search(r"(.*?/v)(\d+)$", prompt_path)
    if not match:
        raise ValueError(f"Could not extract version from path: {prompt_path}")

    base, version = match.groups()
    next_version = int(version) + 1
    return f"{base}{next_version}"


# ---------------- CREWAI SETUP ----------------
refiner = Agent(
    name="Audit Prompt Refiner",
    role="CPA and Audit Expert",
    goal="Refine vague or general audit prompts to be precise and aligned with PCAOB/GAAS.",
    backstory="You are a seasoned audit professional with deep expertise in PCAOB/GAAS standards. "
              "You help transform vague audit instructions into clear, standards-aligned, and actionable tasks.",
    verbose=True,
    llm = llm
)


def refine_prompt(prompt, feedback=None):
    instruction = (
        "Refine this audit prompt for clarity, specificity, and PCAOB/GAAS alignment."
    )
    if feedback:
        instruction += f"\nFeedback to incorporate: {feedback}"

    task = Task(
        description=f"{instruction}\n\nOriginal Prompt:\n{prompt}",
        expected_output="A clear, specific, and PCAOB-aligned version of the prompt.",
        agent=refiner
    )
    crew = Crew(agents=[refiner], tasks=[task])
    return crew.kickoff()


# ------------------------------------------------


# ---------------- GCS HELPERS ----------------
gcs_client = storage.Client()

def read_yaml_from_gcs(bucket, path):
    blob = gcs_client.bucket(bucket).blob(path)
    return yaml.safe_load(blob.download_as_text())


def to_serializable(obj):
    try:
        if isinstance(obj, dict):
            return {k: to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [to_serializable(v) for v in obj]
        elif isinstance(obj, (MappingProxyType, type, property)):
            return None  # Skip unserializable types
        elif isinstance(obj, collections.abc.Mapping):
            return dict(obj)
        elif hasattr(obj, '__dict__'):
            return to_serializable(vars(obj))
        else:
            return obj
    except Exception:
        return str(obj)  # fallback to string if completely unserializable

def write_yaml_to_gcs(bucket, path, content):
    cleaned_content = to_serializable(content)
    blob = gcs_client.bucket(bucket).blob(path)
    blob.upload_from_string(
        yaml.dump(cleaned_content, sort_keys=False),
        content_type='application/x-yaml'
    )

def upload_log_to_log_folder():
    log_bucket = "auditpulse-data"
    log_prefix = "logs/prompt_refinement"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"refinement_log_{timestamp}.log"
    blob = gcs_client.bucket(log_bucket).blob(f"{log_prefix}/{log_filename}")
    blob.upload_from_filename(LOG_FILE)
    logging.info(f"📄 Uploaded central log file to gs://{log_bucket}/{log_prefix}/{log_filename}")


def update_firestore_prompt_path(path):

    db = firestore.Client()

    update_data = {
        "active_prompts_path": path
    }

    try:
        db.collection("config").document("deployment").update(update_data)
        print(f"✅ Updated Firestore field to '{path}'")
    except Exception as e:
        print(f"❌ Failed to update Firestore: {e}")

# ----------------------------------------------


# ---------------- MAIN PIPELINE ----------------
def process_all_runs():
    runs = get_completed_runs_with_prompt_path()
    logging.info(f"🔍 Found {len(runs)} completed runs with prompt_path.")

    for row in runs:
        run_id = row['run_id']
        v0_path = row['prompt_path'].strip("/")
        v0_path = v0_path[v0_path.find("/") + 1 :]
        feedback = row.get("feedback_1", "")

        logging.info(f"\n🔄 Processing run_id {run_id} | Path: {v0_path}")

        # if not v0_path.endswith("/v0"):
        #     logging.warning(f"⚠️ Skipping invalid v0 path: {v0_path}")
        #     continue

        v1_path = get_next_version_path(v0_path)

        try:
            for subfolder in SUBFOLDERS:
                for file_name in ["agents.yaml", "tasks.yaml"]:
                    v0_file = f"{v0_path}/{subfolder}/{file_name}"
                    v1_file = f"{v1_path}/{subfolder}/{file_name}"

                    data = read_yaml_from_gcs(GCS_BUCKET_NAME, v0_file)

                    for key, section in data.items():
                        fields = ['role', 'goal', 'backstory'] if file_name == "agents.yaml" else ['description', 'expected_output']
                        for field in fields:
                            if section.get(field):
                                try:
                                    section[field] = refine_prompt(section[field], feedback)
                                except Exception as e:
                                    logging.warning(f"⚠️ Could not refine {field} for {key} in {subfolder}/{file_name}: {e}")

                    write_yaml_to_gcs(GCS_BUCKET_NAME, v1_file, data)
                    logging.info(f"✅ Saved refined {file_name} to {v1_file}")

            # update_prompt_path_to_v1(run_id, v1_path)
            # logging.info(f"📌 Updated DB with new prompt_path for run_id {run_id}")

            # upload_log_to_gcs(GCS_BUCKET_NAME, v1_path)

        except Exception as e:
            logging.error(f"❌ Failed to process run_id {run_id}: {e}")

        return v1_path
# ------------------------------------------------


# ---------------- RUN ----------------
if __name__ == "__main__":

    v1_path = process_all_runs()
    upload_log_to_log_folder()
    update_firestore_prompt_path(v1_path)
    logging.info("🎉 Refinement pipeline completed.")
