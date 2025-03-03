from datetime import datetime
import os
import json
from pydantic import BaseModel, Field
import re
from google.cloud import storage

def download_companies_data(gcp_file_path='configs/us_public_companies/us_public_companies.json', local_file_path='inputs/us_public_companies.json'):
    """
    Downloads the public companies data file from the specified GCP bucket if not already present locally.

    Args:
        bucket (str): Name of the GCP bucket containing the data.
        gcp_file_path (str): Path to the file in the GCP bucket.
        local_file_path (str): Path where the file should be stored locally.

    Returns:
        None
    """
    if os.path.exists(local_file_path):
        return
    if not os.path.exists(os.path.dirname(local_file_path)):
        os.makedirs(os.path.dirname(local_file_path))

    storage_client = storage.Client(project='auditpulse')
    bucket = storage_client.bucket(bucket_name='auditpulse-data')
    blob = bucket.blob(gcp_file_path)
    blob.download_to_filename(local_file_path)

def load_company_data(file_path):
    """
    Loads company data from a JSON file.

    Args:
        file_path (str): Path to the JSON file containing company data.

    Returns:
        dict: Parsed JSON data containing company details.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

class AuditPulseInputs(BaseModel):
    """Validated and sanitized inputs."""
    company_name: str = Field(..., description="Name of the company to audit.")
    central_index_key: int = Field(..., description="A unique central index key to identify the company.") 
    company_ticker: str = Field(..., description="The ticker associated with the company.") 
    year: str = Field(..., description="Year in which to audit the company.")
    is_valid: bool = Field(..., description="Status indicating the validity of the inputs.")

class DataValidator:
    """
    Handles validation and sanitization of company audit inputs.

    Attributes:
        company_name (str): Name of the company.
        central_index_key (int): Unique identifier for the company.
        year (str): Audit year.
        _companies_data_path (str): Local path for company data file.
        company_data (dict or None): Stores the company details after validation.
        auditpulse_validated_inputs (AuditPulseInputs or None): Stores validated and sanitized inputs.
    """

    def __init__(self, company_name, central_index_key, year):
        """
        Initializes the DataValidator class.

        Args:
            company_name (str): Name of the company.
            central_index_key (int): Unique identifier for the company.
            year (str): Audit year.

        Returns:
            None
        """
        self.auditpulse_validated_inputs = None
        self.company_name = company_name
        self.company_data = None
        self.central_index_key = central_index_key
        self.year = year
        self._companies_data_path = 'inputs/us_public_companies.json'
        download_companies_data(local_file_path=self._companies_data_path)

    def run_validation(self):
        """
        Runs a series of validation checks on the provided inputs.

        Returns:
            tuple: (bool, str) indicating whether validation was successful and a corresponding message.
        """
        is_validated, message = self._validate_cik()
        if not is_validated:
           return is_validated, message
        is_validated, message = self._validate_company_name()
        # if not is_validated:
        #     return is_validated, message
        is_validated, message = self._validate_year()
        if not is_validated:
            return is_validated, message
        self._sanitize_inputs()
        return True, "Inputs validated and sanitized."

    def _validate_cik(self):
        """
        Validates if the provided central index key exists in the company dataset.

        Returns:
            tuple: (bool, str) indicating whether validation was successful and a corresponding message.
        """
        companies_data = load_company_data(self._companies_data_path)
        company_data = companies_data.get(str(self.central_index_key), None)
        if not company_data:
            return False, "Invalid central index key."
        self.company_data = company_data  
        return True, "Central index key is valid."

    def _validate_company_name(self, name_length_threshold: int = 150):
        """
        Validates the company name.

        Args:
            name_length_threshold (int): Maximum allowable length for a company name. Default is 150.

        Returns:
            tuple: (bool, str) indicating whether validation was successful and a corresponding message.
        """
        if not self.company_name.isalnum():
            return False, "Company name must be alphanumeric."
        elif len(self.company_name) > name_length_threshold:
            return False, f"Company name must be less than {name_length_threshold} characters."
        return True, "Company name is valid."
    
    def _validate_year(self):
        """
        Validates the provided year.

        Returns:
            tuple: (bool, str) indicating whether validation was successful and a corresponding message.
        """
        if not self.year.isdigit():
            return False, "Year must be an integer."
        if not re.fullmatch(r'\d{4}', self.year):
            return False, "Invalid year format."
        current_year = datetime.now().year
        if int(self.year) > current_year:
            return False, "Year can't be in the future."
        return True, "Year is valid."
    
    def _sanitize_inputs(self):
        """
        Sanitizes and standardizes the validated inputs.

        Returns:
            None
        """
        self.company_name = self.company_name.strip()
        self.year = self.year.strip()
        self.auditpulse_validated_inputs = AuditPulseInputs(
            company_name=self.company_data.get('title'),
            central_index_key=self.company_data.get('cik_str'),
            company_ticker=self.company_data.get('ticker'),
            year=self.year,
            is_valid=True
        )

def main():
    company_name = "NVIDIA CORP"
    central_index_key = "1045810"
    year = "2025"
    validator = DataValidator(company_name, 
                              central_index_key, 
                              year
                                )
    validator.run_validation()
    print(f"Output:\n{validator.auditpulse_validated_inputs}")
                        

if __name__ == '__main__':
    main()
