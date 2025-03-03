import os
import logging
from sec_edgar_downloader import Downloader
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# List of company tickers (Modify this as needed)
'''
tickers = [
"MSFT", "CSCO", "GOOGL", "PFE", "AMGN", "MRK", "BAC", "GS", "WFC",
"TSLA", "MCD", "HD", "KO", "PM", "PEP", "CVX", "EOG", "COP", "CAT",
"MMM", "UNP", "NEE", "AEP", "D", "VZ", "CHTR", "TMUS", "PLD", "BXP", "PSA",
"AAPL", "JNJ", "JPM", "AMZN", "PG", "XOM", "BA", "DUK", "T", "SPG",
"INTC", "ABT", "C", "NKE", "WMT", "SLB", "GE", "SO", "CMCSA", "AVB"
]
'''
tickers = ["MSFT"]

AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/opt/airflow")
basePath = os.path.join(AIRFLOW_HOME, "data")
os.makedirs(basePath, exist_ok=True)

# Initialize the downloader with a user agent
dl = Downloader("my_company", "my_email@example.com", download_folder=basePath)

def extract_text_from_html(html_file):
    with open(html_file, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def remove_specific_files(folder_path):
    files_to_remove = ['full-submission.txt', 'primary-document.html']
    for file_name in files_to_remove:
        file_path = os.path.join(folder_path, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Removed {file_path}")
        else:
            logger.warning(f"File {file_path} not found, skipping")

def process_tickers(tickers):
    for ticker in tickers:
        logger.info(f"Downloading 10-K for {ticker}...")
        logger.debug("Testing")

        dl.get("10-K", ticker, limit=1, download_details=True)

        company_dir = os.path.join(basePath, "sec-edgar-filings", ticker, "10-K")

        if not os.path.exists(company_dir):
            logger.error(f"No filings found for {ticker}, skipping...")
            continue

        dynamic_folders = [folder for folder in os.listdir(company_dir) if
                           os.path.isdir(os.path.join(company_dir, folder))]

        if not dynamic_folders:
            logger.error(f"No subfolders found inside 10-K for {ticker}, skipping...")
            continue

        for dynamic_folder in dynamic_folders:
            logger.info(f"Found dynamic folder: {dynamic_folder}")

            dynamic_folder_path = os.path.join(company_dir, dynamic_folder)
            html_files = [f for f in os.listdir(dynamic_folder_path) if
                          f.endswith(".html")]

            if not html_files:
                logger.error(f"No HTML files found in {dynamic_folder} for {ticker}, skipping...")
                continue

            latest_html_file = os.path.join(dynamic_folder_path, html_files[0])

            extracted_text = extract_text_from_html(latest_html_file)

            text_file_path = os.path.join(dynamic_folder_path,
                                          f"{ticker}_10K_{dynamic_folder}.txt")
            with open(text_file_path, "w", encoding="utf-8") as txt_file:
                txt_file.write(extracted_text)

            remove_specific_files(dynamic_folder_path)
            logger.info(f"{ticker} processed: Text saved to {text_file_path}.")

    logger.info("All reports processed successfully!")

if __name__ == "__main__":
    process_tickers(tickers)
