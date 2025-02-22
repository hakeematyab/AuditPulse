import os
import pytest
from unittest.mock import MagicMock, patch, mock_open
from bs4 import BeautifulSoup
from DataProcessing.Processor_10K.dags.extractor_10K import extract_text_from_html, remove_specific_files

# Sample HTML content for testing
SAMPLE_HTML = """
<html>
  <head><title>Test Document</title></head>
  <body>
    <p>Company Report</p>
    <p>Financial Data</p>
  </body>
</html>
"""

@pytest.fixture
def sample_html_file(tmp_path):
    """Creates a temporary HTML file for testing."""
    html_file = tmp_path / "test.html"
    html_file.write_text(SAMPLE_HTML, encoding="utf-8")
    return html_file

def test_extract_text_from_html(sample_html_file):
    """Test if extract_text_from_html correctly extracts text from HTML."""
    extracted_text = extract_text_from_html(sample_html_file)
    expected_text = "Test Document\nCompany Report\nFinancial Data"
    assert extracted_text == expected_text

@patch("os.path.exists", return_value=True)
@patch("os.remove")
def test_remove_specific_files(mock_remove, mock_exists, tmp_path):
    """Test if remove_specific_files correctly removes specified files."""
    folder_path = tmp_path / "test_folder"
    os.makedirs(folder_path)

    # Create test files
    file1 = folder_path / "full-submission.txt"
    file2 = folder_path / "primary-document.html"
    file1.touch()
    file2.touch()

    remove_specific_files(str(folder_path))

    # Assert os.remove() was called twice
    mock_remove.assert_any_call(str(file1))
    mock_remove.assert_any_call(str(file2))
    assert mock_remove.call_count == 2

@patch("DataProcessing.Processor_10K.dags.extractor_10K.Downloader.get")
def test_download_10k(mock_get):
    """Test if the downloader correctly calls sec_edgar_downloader."""
    mock_get.return_value = None  # Mock the download method

    from DataProcessing.Processor_10K.dags.extractor_10K import dl

    ticker = "AAPL"
    dl.get("10-K", ticker, limit=5, download_details=True)

    mock_get.assert_called_once_with("10-K", ticker, limit=5, download_details=True)

