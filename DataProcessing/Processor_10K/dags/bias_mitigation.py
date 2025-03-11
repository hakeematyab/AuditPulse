import os
import json
import yfinance as yf
import matplotlib.pyplot as plt
from collections import defaultdict
from scipy.stats import chisquare
import random
import shutil

# Base directory containing SEC filings
base_dir = "/opt/airflow/data/sec-edgar-filings/"

# Path to save the ticker-sector mapping
sector_mapping_path = "ticker_sector_mapping.json"

# Step 1: Map Tickers to Sectors
def get_sector(ticker):
    """Fetches the sector for a given ticker using Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        sector = stock.info.get("sector", "Unknown")
        
        # Retry if sector mapping fails
        if sector == "Unknown":
            print(f"⚠️ Retrying sector mapping for {ticker}")
            stock = yf.Ticker(ticker)
            sector = stock.info.get("sector", "Unknown")
        
        # Log if still unknown
        if sector == "Unknown":
            print(f"❌ Sector mapping failed for {ticker}")
        
        return sector
    except Exception as e:
        print(f"Error fetching sector for {ticker}: {e}")
        return "Unknown"

def map_tickers_to_sectors(data_path):
    """Maps tickers to sectors by traversing the directory structure."""
    sector_map = {}
    for ticker in os.listdir(data_path):
        ticker_path = os.path.join(data_path, ticker)
        if os.path.isdir(ticker_path):
            ten_k_path = os.path.join(ticker_path, "10-K")
            if os.path.exists(ten_k_path):
                for filing_folder in os.listdir(ten_k_path):
                    filing_path = os.path.join(ten_k_path, filing_folder)
                    if os.path.isdir(filing_path):
                        for file in os.listdir(filing_path):
                            if file.endswith(".json"):  # Check for JSON report
                                if ticker not in sector_map:
                                    sector = get_sector(ticker)
                                    sector_map[ticker] = sector
                                break  # Stop after finding the first JSON file
                        if ticker in sector_map:
                            break  # Move to next ticker
    return sector_map

def save_sector_mapping(sector_map, path):
    """Saves the ticker-sector mapping to a JSON file."""
    with open(path, "w") as f:
        json.dump(sector_map, f, indent=4)
    print("Ticker to sector mapping saved.")

# Step 2: Analyze Bias in Sector Distribution
def count_lines_in_json_file(json_path):
    """Counts the number of lines in a JSON file."""
    with open(json_path, 'r') as f:
        return sum(1 for _ in f)

def analyze_lines_by_sector(data_path, ticker_sector_map):
    """Analyzes cumulative number of lines in reports for each sector."""
    sector_lines = defaultdict(int)
    for ticker_folder in os.listdir(data_path):
        ticker = ticker_folder
        if ticker in ticker_sector_map:
            sector = ticker_sector_map[ticker]
            ten_k_path = os.path.join(data_path, ticker, "10-K")
            if os.path.exists(ten_k_path):
                for filing_folder in os.listdir(ten_k_path):
                    filing_path = os.path.join(ten_k_path, filing_folder)
                    if os.path.isdir(filing_path):
                        for file in os.listdir(filing_path):
                            if file.endswith(".json"):
                                json_path = os.path.join(filing_path, file)
                                lines = count_lines_in_json_file(json_path)
                                sector_lines[sector] += lines
    return sector_lines


def check_sector_bias(observed_distribution, original_distribution):
    """Improved Chi-square test to compare observed vs. expected sector distribution."""
    
    # Ensure all sectors are accounted for (even missing ones)
    all_sectors = set(original_distribution.keys()).union(set(observed_distribution.keys()))
    
    # Fill missing sectors with zero entries
    observed_filled = {sector: observed_distribution.get(sector, 0) for sector in all_sectors}
    original_filled = {sector: original_distribution.get(sector, 0) for sector in all_sectors}
    
    # Calculate expected distribution proportionally based on original data
    total_observed = sum(observed_filled.values())
    total_original = sum(original_filled.values())
    
    expected_distribution = {
        sector: (original_filled[sector] / total_original) * total_observed
        for sector in all_sectors
    }

    observed = list(observed_filled.values())
    expected = list(expected_distribution.values())

    chi2, p_value = chisquare(observed, expected)
    
    return chi2, p_value

def plot_sector_distribution(sector_distribution, original_distribution, title="Sector Distribution"):
    """Visualizes the cumulative number of lines by sector, ensuring all sectors are displayed."""
    
    # Include all sectors from the original distribution, even if missing in oversampled data
    all_sectors = set(original_distribution.keys()).union(set(sector_distribution.keys()))

    # Fill missing sectors with zero counts
    filled_distribution = {sector: sector_distribution.get(sector, 0) for sector in all_sectors}

    sectors = list(filled_distribution.keys())
    lines = [filled_distribution[sector] for sector in sectors]

    plt.figure(figsize=(12, 6))
    plt.bar(sectors, lines, color='skyblue')
    plt.xlabel('Sector')
    plt.ylabel('Cumulative Number of Lines in Reports')
    plt.title(title)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

# Step 3: Mitigate Bias Using Oversampling
def calculate_oversampling_targets(observed_distribution):
    """Calculates additional lines required for underrepresented sectors only."""
    total_lines = sum(observed_distribution.values())
    expected_value = total_lines / len(observed_distribution)
    
    oversampling_targets = {}
    for sector, lines in observed_distribution.items():
        # Only focus on sectors significantly underrepresented (<90% of expected value)
        if lines < expected_value * 0.7:  
            oversampling_targets[sector] = int(expected_value - lines)
    
    return oversampling_targets


def is_distribution_balanced(observed_distribution, tolerance=0.03):
    total_lines = sum(observed_distribution.values())
    expected_value = total_lines / len(observed_distribution)
    for lines in observed_distribution.values():
        if abs(lines - expected_value) / expected_value > tolerance:
            return False
    return True

def oversample_reports(base_path, ticker_sector_map, observed_distribution, tolerance=0.03):
    """
    Oversamples underrepresented sectors in a controlled manner and ensures balance.

    Args:
        base_path (str): Base directory containing SEC filings.
        ticker_sector_map (dict): Mapping of tickers to their respective sectors.
        observed_distribution (dict): Observed line counts for each sector.
        tolerance (float): Acceptable deviation as a fraction of the expected value (default: 3%).

    Returns:
        dict: Updated observed distribution after oversampling.
    """
    total_lines = sum(observed_distribution.values())
    num_sectors = len(observed_distribution)
    expected_value = total_lines / num_sectors  # Expected lines per sector

    # Calculate oversampling targets for underrepresented sectors
    oversampling_targets = {
        sector: int(expected_value - lines)
        for sector, lines in observed_distribution.items()
        if lines < expected_value * (1 - tolerance)
    }

    print(f"Expected lines per sector: {expected_value}")
    print(f"Oversampling targets: {oversampling_targets}")

    # Perform controlled oversampling
    for ticker, sector in ticker_sector_map.items():
        if sector in oversampling_targets:
            target_lines = oversampling_targets[sector]
            ten_k_path = os.path.join(base_path, ticker, "10-K")
            
            if not os.path.exists(ten_k_path):
                continue
            
            total_added_lines = 0
            found_data = False
            
            for filing_folder in os.listdir(ten_k_path):
                filing_path = os.path.join(ten_k_path, filing_folder)
                if os.path.isdir(filing_path):
                    json_files = [f for f in os.listdir(filing_path) if f.endswith(".json") and "copy" not in f]
                    if not json_files:
                        continue
                    
                    # Distribute added lines proportionally across available files
                    for original_file in json_files:
                        json_path = os.path.join(filing_path, original_file)
                        with open(json_path, 'r') as f:
                            content = f.readlines()
                        
                        # Add lines only if the target has not been reached
                        while total_added_lines < target_lines:
                            duplicate_filename = f"{original_file.replace('.json', '')}_copy_{total_added_lines}.json"
                            duplicate_path = os.path.join(filing_path, duplicate_filename)
                            
                            with open(duplicate_path, 'w') as new_file:
                                new_file.writelines(content)
                            
                            total_added_lines += len(content)
                            observed_distribution[sector] += len(content)
                            
                            if total_added_lines >= target_lines:
                                print(f"✅ Oversampled {sector}: Added {total_added_lines} lines")
                                break
                    
                    if total_added_lines >= target_lines:
                        break
            
            if total_added_lines == 0:
                print(f"⚠️ Warning: No sufficient data found to oversample for sector: {sector}")
    
    # Post-check distribution
    print("\nFinal distribution after controlled oversampling:")
    for sector, lines in observed_distribution.items():
        print(f"{sector}: {lines} lines")
    
    return observed_distribution


# Step 4: Analyze Oversampled Data
def analyze_oversampled_distribution(base_dir, ticker_sector_map):
    """Analyzes the cumulative number of lines in oversampled data for each sector."""
    sector_lines = defaultdict(int)
    
    for ticker_folder in os.listdir(base_dir):
        ticker = ticker_folder
        if ticker in ticker_sector_map:
            sector = ticker_sector_map[ticker]
            ten_k_path = os.path.join(base_dir, ticker, "10-K")
            
            if os.path.exists(ten_k_path):
                found_files = False
                
                for filing_folder in os.listdir(ten_k_path):
                    filing_path = os.path.join(ten_k_path, filing_folder)
                    if os.path.isdir(filing_path):
                        for file in os.listdir(filing_path):
                            if file.endswith(".json"):
                                json_path = os.path.join(filing_path, file)
                                lines = count_lines_in_json_file(json_path)
                                sector_lines[sector] += lines
                                found_files = True

                # Warning if no files were detected
                if not found_files:
                    print(f"⚠️ No JSON files found for {ticker} in oversampled data.")
    
    return sector_lines
def clear_oversampled_files(base_dir):
    """
    Deletes all JSON files containing 'copy' in their filenames from the directory structure.
    
    Args:
        base_dir (str): The base directory containing SEC filings.
    """
    deleted_files_count = 0
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".json") and "copy" in file:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                    deleted_files_count += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
    
    print(f"\n✅ Total oversampled files deleted: {deleted_files_count}")

# Main Workflow
if __name__ == "__main__":
    
    # Clear any existing oversampled files
    print("Clearing existing oversampled JSON files...")
    clear_oversampled_files(base_dir)
    
    # Step 1: Map Tickers to Sectors
    print("Mapping tickers to sectors...")
    
    if not os.path.exists(sector_mapping_path):
        sector_map = map_tickers_to_sectors(base_dir)
        save_sector_mapping(sector_map, sector_mapping_path)
    
    # Load existing mapping
    with open(sector_mapping_path, 'r') as f:
        ticker_sector_map = json.load(f)

    # Step 2: Analyze Bias Before Mitigation
    print("\nAnalyzing bias before mitigation...")
    observed_distribution = analyze_lines_by_sector(base_dir, ticker_sector_map)
    original_distribution = observed_distribution.copy()  # Original data before mitigation

    chi2_before, p_value_before = check_sector_bias(observed_distribution, original_distribution)
    print(f"Chi2 (Before): {chi2_before}, p-value (Before): {p_value_before}")

    plot_sector_distribution(observed_distribution, original_distribution, title="Sector Distribution Before Mitigation")

    # Step 3: Mitigate Bias Using Oversampling
    print("\nMitigating bias through oversampling...")
    oversampled_distribution = oversample_reports(base_dir, ticker_sector_map, observed_distribution.copy())

    # Step 4: Analyze Oversampled Distribution
    print("\nAnalyzing oversampled data...")
    if not oversampled_distribution:
        print("❌ No oversampled data found — check oversampling logic.")
    else:
        chi2_after, p_value_after = check_sector_bias(oversampled_distribution, original_distribution)
        print(f"Chi2 (After): {chi2_after}, p-value (After): {p_value_after}")
        plot_sector_distribution(oversampled_distribution, original_distribution, title="Sector Distribution After Mitigation")


