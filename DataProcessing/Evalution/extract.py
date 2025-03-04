import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://www.sec.gov/Archives/edgar/data/1326801/000132680124000012/meta-20231231.htm"
response = requests.get(url)
response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
html_content = response.text

soup = BeautifulSoup(html_content, "html.parser")

text_content = soup.get_text(separator="\n", strip=True)
print(text_content)

tables = soup.find_all("table")
for index, table in enumerate(tables):
    df = pd.read_html(str(table))[0]
    print(f"Table {index + 1}:\n", df)

table = soup.find("table", {"id": "your-table-id"}) # or {"class": "your-table-class"}
if table:
    df = pd.read_html(str(table))[0]
    print(df)