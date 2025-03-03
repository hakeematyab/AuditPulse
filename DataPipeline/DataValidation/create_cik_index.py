import json

def load_company_tickers(file_path):
    """
    Load the JSON file containing company tickers.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def build_cik_index(data):
    """
    Build an index mapping CIK values (as strings without leading zeros)
    to their corresponding company records.
    """
    index = {}
    for record in data.values():
        cik = int(record.get("cik_str"))
        index[cik] = record
    return index

data = load_company_tickers("us_public_companies.json")
cik_index = build_cik_index(data)
with open("cik_index.json", "w") as f:
    json.dump(cik_index, f, indent=2)