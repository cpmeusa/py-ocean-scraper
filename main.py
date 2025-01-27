import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import pandas as pd
from webdriver_manager.chrome import ChromeDriverManager
import requests
import json
try:
    from config import (
        SERVICE_ACCOUNT_CREDS, 
        MINER_ADDRESS, 
        SHEET_ID, 
        CHECK_INTERVAL
    )
except ImportError:
    print("Error: config.py not found or missing required variables")
    exit(1)

# Configuration
MINER_ADDRESS = "bc1q48qqqq77h8tvmy7pqh4h3t3cmsfk6d8f5c7vjt"
SHEET_ID = "1Ik8q-FptgJzx-Ya17WG6p8wwLQO_FUTdZQLQSmDQQNs"
CHECK_INTERVAL = 3600  # Check every hour

BTC_PRICE_CACHE_FILE = "btc_price_cache.json"

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_ocean_data(driver):
    try:
        url = f"https://ocean.xyz/stats/{MINER_ADDRESS}"
        driver.get(url)
        
        download_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[@class='csv-download-button' and contains(text(), 'Download CSV')]"))
        )
        download_button.click()
        time.sleep(5)
        
        downloads_path = os.path.expanduser("~/Downloads")
        csv_files = [f for f in os.listdir(downloads_path) if f.endswith('.csv')]
        latest_csv = max([os.path.join(downloads_path, f) for f in csv_files], key=os.path.getctime)
        
        df = pd.read_csv(latest_csv)
        df['Time'] = pd.to_datetime(df['Time'])
        df['Share Log %'] = df['Share Log %'].str.rstrip('%').astype(float)
        
        os.remove(latest_csv)
        return df
    except Exception as e:
        print(f"Error fetching Ocean data: {str(e)}")
        return None

def load_btc_price_cache():
    try:
        if os.path.exists(BTC_PRICE_CACHE_FILE):
            with open(BTC_PRICE_CACHE_FILE, "r") as file:
                return json.load(file)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {BTC_PRICE_CACHE_FILE}. Creating a new cache file.")
        return {}
    return {}

def save_btc_price_cache(cache):
    with open(BTC_PRICE_CACHE_FILE, "w") as file:
        json.dump(cache, file, indent=4)

def get_historical_price(timestamp):
    timestamp_str = str(timestamp)
    btc_price_cache = load_btc_price_cache()
    
    if timestamp_str in btc_price_cache:
        return btc_price_cache[timestamp_str]
    
    try:
        time.sleep(1)
        url = f"https://min-api.cryptocompare.com/data/pricehistorical"
        params = {
            'fsym': 'BTC',
            'tsyms': 'USD',
            'ts': int(timestamp.timestamp())
        }
        response = requests.get(url, params=params)
        price = response.json()['BTC']['USD']
        
        btc_price_cache[timestamp_str] = price
        save_btc_price_cache(btc_price_cache)
        
        return price
    except requests.exceptions.RequestException as e:
        print(f"Error fetching BTC price for timestamp {timestamp}: {str(e)}")
        return None

def update_sheet(data):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_CREDS, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    
    # Get current BTC price safely
    try:
        current_btc_price = get_historical_price(pd.Timestamp.now()) or ''
    except:
        current_btc_price = ''
    
    # Format current BTC price as currency
    current_btc_price_formatted = f'${current_btc_price:,.2f}' if current_btc_price else ''
    
    # Get current timestamp in human-readable format
    current_timestamp = datetime.now().strftime('%B %d, %Y %I:%M %p')
    
    # Create header rows
    report_header_row = [f'Report as of: {current_timestamp}', '', '', '', '', '', '', '', '', '', '']
    price_header_row = [f'BTC Price: {current_btc_price_formatted}', '', '', '', '', '', '', '', '', '', '']
    empty_row = ['', '', '', '', '', '', '', '', '', '', '']
    
    headers = [['Time', 'Block', 'Share %', 'Share Count', 'Earnings (BTC)', 'Pool Fees (BTC)', 'BTC Price (USD)', 'Cost Basis (USD)', 'Pool Fees Cost Basis (USD)', 'Current Value (USD)', 'Gain/Loss (USD)']]
    
    # Format data
    data['Block'] = data['Block'].apply(lambda x: f'=HYPERLINK("https://mempool.space/block/{x}", "{x}")')
    
    # Fetch historical BTC prices for each timestamp
    data['BTC Price (USD)'] = data['Time'].apply(get_historical_price)
    
    # Calculate USD values using formulas with dynamic row references
    data['Cost Basis (USD)'] = data.apply(lambda row: f'=E{row.name + 5}*G{row.name + 5}', axis=1)
    data['Pool Fees Cost Basis (USD)'] = data.apply(lambda row: f'=F{row.name + 5}*G{row.name + 5}', axis=1)
    
    data['Time'] = data['Time'].dt.strftime('%m/%d/%y %H:%M:%S')
    data = data.replace({float('nan'): '', 'NaN': ''})
    values = [report_header_row, price_header_row, empty_row] + headers + data.values.tolist()
    
    totals_row_index = len(values) + 1
    totals_row = ['Total', '', '', '', f'=SUM(E5:E{totals_row_index - 1})', f'=SUM(F5:F{totals_row_index - 1})', current_btc_price, f'=SUM(H5:H{totals_row_index - 1})', f'=SUM(I5:I{totals_row_index - 1})', f'=SUM(J5:J{totals_row_index - 1})', f'=SUM(K5:K{totals_row_index - 1})']
    values.append(totals_row)
    
    # Calculate current value and gain/loss using formulas with dynamic row references and current BTC price cell
    current_value_formulas = [f'=E{row + 5}*$G${totals_row_index}' for row in range(len(data))]
    gain_loss_formulas = [f'=J{row + 5}-H{row + 5}' for row in range(len(data))]
    
    for row, formula in zip(data.itertuples(index=True), current_value_formulas):
        values[row.Index + 4].append(formula)
    
    for row, formula in zip(data.itertuples(index=True), gain_loss_formulas):
        values[row.Index + 4].append(formula)
    
    # Unmerge cells in the specified range
    sheet.batchUpdate(
        spreadsheetId=SHEET_ID,
        body={
            "requests": [
                {
                    "unmergeCells": {
                        "range": {
                            "sheetId": 0,
                            "startRowIndex": 0,
                            "endRowIndex": len(data) + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(data.columns)
                        }
                    }
                }
            ]
        }
    ).execute()
    
    # Clear and update
    service.spreadsheets().values().clear(
        spreadsheetId=SHEET_ID,
        range='Sheet1!A1:F',
        body={}
    ).execute()

    # Update values
    update_body = {'values': values}
    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range='Sheet1!A1',
        valueInputOption='USER_ENTERED',
        body=update_body
    ).execute()

    # Clear existing formatting
    clear_format_body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": len(values)},
                    "cell": {"userEnteredFormat": {}},
                    "fields": "userEnteredFormat"
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID,
        body=clear_format_body
    ).execute()
    
    # Apply new formatting
    format_body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 2},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}, "horizontalAlignment": "LEFT"}},
                    "fields": "userEnteredFormat(textFormat,horizontalAlignment)"
                }
            },
            {
                "mergeCells": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": totals_row_index - 1,
                        "endRowIndex": totals_row_index,
                        "startColumnIndex": 0,
                        "endColumnIndex": 4
                    },
                    "mergeType": "MERGE_ALL"
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": totals_row_index - 1, "endRowIndex": totals_row_index},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}, "horizontalAlignment": "RIGHT"}},
                    "fields": "userEnteredFormat(textFormat,horizontalAlignment)"
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 4, "endRowIndex": totals_row_index, "startColumnIndex": 0, "endColumnIndex": 1},
                    "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE_TIME"}}},
                    "fields": "userEnteredFormat.numberFormat"
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 4, "endRowIndex": totals_row_index, "startColumnIndex": 6, "endColumnIndex": 11},
                    "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"}}},
                    "fields": "userEnteredFormat.numberFormat"
                }
            },
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{"sheetId": 0, "startRowIndex": 4, "endRowIndex": totals_row_index, "startColumnIndex": 10, "endColumnIndex": 11}],
                        "booleanRule": {
                            "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0"}]},
                            "format": {
                                "textFormat": {"foregroundColor": {"red": 0.8, "green": 0.0, "blue": 0.0}}
                            }
                        }
                    }
                }
            },
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{"sheetId": 0, "startRowIndex": 4, "endRowIndex": totals_row_index, "startColumnIndex": 10, "endColumnIndex": 11}],
                        "booleanRule": {
                            "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
                            "format": {
                                "textFormat": {"foregroundColor": {"red": 0.0, "green": 0.8, "blue": 0.0}}
                            }
                        }
                    }
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 3, "endRowIndex": 4},
                    "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
                    "fields": "userEnteredFormat.wrapStrategy"
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID,
        body=format_body
    ).execute()

def main():
    driver = None
    try:
        driver = setup_driver()
        print(f"Checking data at {datetime.now()}")
        df = get_ocean_data(driver)
        if df is not None:  # Only update if we got data
            update_sheet(df)
            print("Data updated successfully")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    print(f"Starting Ocean Mining tracker at {datetime.now()}")
    main()