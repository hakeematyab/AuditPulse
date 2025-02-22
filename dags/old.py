from sec_edgar_downloader import Downloader
import os
from datetime import datetime

# Create a directory to store all downloads
AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/Users/aniketgupta/airflow")
base_dir = os.path.join(AIRFLOW_HOME, "data/SEC_10K_Filings")
os.makedirs(base_dir, exist_ok=True)


# Company information dictionary
companies = {
  "Technology": [
    {"name": "Microsoft Corporation", "ticker": "MSFT", "domain": "Software"}
  ],
  # Add other categories as needed
}


def download_10k_filings(company_info, start_year=2022, end_year=2023):
  """
  Download 10-K filings for a specific company
  """
  # Create downloader instance for each company
  dl = Downloader(
      company_name=f"{company_info['name']} {company_info['ticker']}",
      email_address = "test@gmail.com",
      download_folder = base_dir
  )

  # Create company-specific directory
  company_dir = os.path.join(base_dir, company_info['ticker'])
  os.makedirs(company_dir, exist_ok=True)

  print(
    f"\nDownloading 10-K filings for {company_info['name']} ({company_info['ticker']})")

  # Download filings for each year
  for year in range(start_year, end_year + 1):
    try:
      print(f"Downloading year {year}...")
      dl.get(
          "10-K",
          company_info['ticker'],
          limit=1,
          after=f"{year}-01-01",
          before=f"{year}-12-31"
      )
    except Exception as e:
      print(
        f"Error downloading {year} filing for {company_info['ticker']}: {str(e)}")


def main():
  # Create log file
  log_file = os.path.join(base_dir,
                          f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

  with open(log_file, 'w') as f:
    f.write(f"10-K Download Log - Started at {datetime.now()}\n\n")

  # Process each category and company
  for category, company_list in companies.items():
    print(f"\nProcessing {category} companies...")

    for company in company_list:
      try:
        download_10k_filings(company)

        # Log successful download
        with open(log_file, 'a') as f:
          f.write(
            f"Successfully processed {company['name']} ({company['ticker']})\n")

      except Exception as e:
        # Log any errors
        with open(log_file, 'a') as f:
          f.write(
            f"Error processing {company['name']} ({company['ticker']}): {str(e)}\n")


if __name__ == "__main__":
  print("Starting SEC 10-K filing downloads...")
  main()
  print("\nDownload process completed. Check the log file for details.")
