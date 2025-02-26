import os
from sec_edgar_downloader import Downloader
from bs4 import BeautifulSoup


# List of company tickers (Modify this as needed)
# tickers = [
#     "MSFT", "CSCO", "GOOGL", "PFE", "AMGN", "MRK", "BAC", "GS", "WFC",
#     "TSLA", "MCD", "HD", "KO", "PM", "PEP", "CVX", "EOG", "COP", "CAT",
#     "MMM", "UNP", "NEE", "AEP", "D", "VZ", "CHTR", "TMUS", "PLD", "BXP", "PSA",
#     "AAPL", "JNJ", "JPM", "AMZN", "PG", "XOM", "BA", "DUK", "T", "SPG",
#     "INTC", "ABT", "C", "NKE", "WMT", "SLB", "GE", "SO", "CMCSA", "AVB"
# ]

tickers = [
    "MSFT"
]

AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/opt/airflow")
basePath = os.path.join(AIRFLOW_HOME, "data")
os.makedirs(basePath, exist_ok=True)

# Initialize the downloader with a user agent
dl = Downloader("my_company", "my_email@example.com", download_folder = basePath)

# Function to extract text from HTML files
def extract_text_from_html(html_file):
  with open(html_file, "r", encoding="utf-8") as file:
    soup = BeautifulSoup(file, "html.parser")
  return soup.get_text(separator="\n", strip=True)

# Function to clean up specific files in the folder
def remove_specific_files(folder_path):
    files_to_remove = ['full-submission.txt', 'primary-document.html']
    for file_name in files_to_remove:
        file_path = os.path.join(folder_path, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)  # Remove the specified file
            print("Removed {}".format(file_path))
        else:
          print("File {} not found, skipping".format(file_path))

# Download the latest 10-K filings and save extracted text for each company
def process_tickers(tickers):
  for ticker in tickers:
    print(f"Downloading 10-K for {ticker}...")

    # Download the latest 5 filings (limit=5)
    dl.get("10-K", ticker, limit=1, download_details=True)

    # Locate the downloaded filing directory
    company_dir = os.path.join(basePath,"sec-edgar-filings", ticker, "10-K")

    if not os.path.exists(company_dir):
      print(f"❌ No filings found for {ticker}, skipping...")
      continue

    # Find all dynamic folders inside 10-K (there could be multiple)
    dynamic_folders = [folder for folder in os.listdir(company_dir) if
                       os.path.isdir(os.path.join(company_dir, folder))]

    if not dynamic_folders:
      print(f"❌ No subfolders found inside 10-K for {ticker}, skipping...")
      continue

    # Process each dynamic folder
    for dynamic_folder in dynamic_folders:
      print(f"Found dynamic folder: {dynamic_folder}")

      # Get the latest downloaded HTML file from the dynamic folder
      dynamic_folder_path = os.path.join(company_dir, dynamic_folder)
      html_files = [f for f in os.listdir(dynamic_folder_path) if
                    f.endswith(".html")]

      if not html_files:
        print(
          f"❌ No HTML files found in {dynamic_folder} for {ticker}, skipping...")
        continue

      latest_html_file = os.path.join(dynamic_folder_path, html_files[0])

      # Extract text from the HTML file
      extracted_text = extract_text_from_html(latest_html_file)

      # Save extracted text as a .txt file
      text_file_path = os.path.join(dynamic_folder_path,
                                    f"{ticker}_10K_{dynamic_folder}.txt")
      with open(text_file_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(extracted_text)

      remove_specific_files(dynamic_folder_path)
      print(f"✅ {ticker} processed: Text saved to {text_file_path}.")

  print("All reports processed successfully!")

if __name__ == "__main__":
    process_tickers(tickers)