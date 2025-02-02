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
    options.add_argument('--ignore-certificate-errors')
    downloads_path = os.path.expanduser("~/ocean_tracker_downloads")
    if not os.path.exists(downloads_path):
        os.makedirs(downloads_path)
        print("Created downloads folder:", downloads_path)
    else:
        print("Using existing downloads folder:", downloads_path)
    
    # Set download preferences so the CSV is automatically saved to the dedicated folder
    prefs = {
        "download.default_directory": downloads_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    # Enable file downloads in headless mode
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": downloads_path})
    return driver

def get_ocean_data(driver):
    try:
        url = f"https://ocean.xyz/stats/{MINER_ADDRESS}"
        driver.get(url)
        time.sleep(5)  # Allow page to load
        earnings_form = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "//form[contains(@action, '/earnings')]")
            )
        )
        print("Earnings form located. Submitting via POST using requests.")
        action_url = earnings_form.get_attribute("action")
        if not action_url.startswith("http"):
            action_url = "https://ocean.xyz" + action_url
        s = requests.Session()
        for cookie in driver.get_cookies():
            s.cookies.set(cookie['name'], cookie['value'])
        response = s.post(action_url)
        if response.status_code == 200:
            from io import StringIO
            csv_text = response.content.decode('utf-8')
            df = pd.read_csv(StringIO(csv_text))
            df['Time'] = pd.to_datetime(df['Time'])
            df['Share Log %'] = df['Share Log %'].str.rstrip('%').astype(float)
            return df
        else:
            print("Failed to download earnings CSV via requests. Status code:", response.status_code)
            return None
    except Exception as e:
        print(f"Error fetching Ocean data: {str(e)}")
        return None

def get_ocean_payouts(driver):
    try:
        url = f"https://ocean.xyz/stats/{MINER_ADDRESS}"
        driver.get(url)
        time.sleep(5)  # Allow page to load
        payouts_form = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "//form[contains(@action, 'payouts')]")
            )
        )
        print("Payouts form located. Submitting via POST using requests.")
        action_url = payouts_form.get_attribute("action")
        if not action_url.startswith("http"):
            action_url = "https://ocean.xyz" + action_url
        s = requests.Session()
        for cookie in driver.get_cookies():
            s.cookies.set(cookie['name'], cookie['value'])
        response = s.post(action_url)
        if response.status_code == 200:
            from io import StringIO
            csv_text = response.content.decode('utf-8')
            df = pd.read_csv(StringIO(csv_text))
            return df
        else:
            print("Failed to download payouts CSV via requests. Status code:", response.status_code)
            return None
    except Exception as e:
        print(f"Error fetching Ocean payouts data: {str(e)}")
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
    
    # Retrieve the sheetId for the "Earnings" sheet so that formatting only applies there
    earnings_sheet_id = None
    spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    for s in spreadsheet.get("sheets", []):
        if s["properties"]["title"] == "Earnings":
            earnings_sheet_id = s["properties"]["sheetId"]
            break
    if earnings_sheet_id is None:
        # If no "Earnings" sheet exists, create one.
        add_sheet_request = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": "Earnings",
                            "gridProperties": {
                                "rowCount": 1000,
                                "columnCount": 11
                            }
                        }
                    }
                }
            ]
        }
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID,
            body=add_sheet_request
        ).execute()
        earnings_sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
        print("Created new 'Earnings' sheet with sheetId:", earnings_sheet_id)
    
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
    
    # Update the data DataFrame to include formulas for Cost Basis and Pool Fees Cost Basis
    data['Cost Basis (USD)'] = data.apply(lambda row: f'=E{row.name + 5}*G{row.name + 5}', axis=1)
    data['Pool Fees Cost Basis (USD)'] = data.apply(lambda row: f'=F{row.name + 5}*G{row.name + 5}', axis=1)
    
    data['Time'] = data['Time'].dt.strftime('%m/%d/%y %H:%M:%S')
    data = data.replace({float('nan'): '', 'NaN': ''})
    
    # Define table header row for the Earnings sheet with additional columns:
    earnings_headers = ['Time', 'Block', 'Share %', 'Share Count', 'Earnings (BTC)', 'Pool Fees (BTC)', 'BTC Price (USD)', 'Cost Basis (USD)', 'Pool Fees Cost Basis (USD)', 'Current Value (USD)', 'Gain/Loss (USD)']
    
    # Prepare final values by combining header rows with the data rows
    values = [report_header_row, price_header_row, empty_row, earnings_headers] + data.values.tolist()
    
    totals_row_index = len(values) + 1
    totals_row = [
        'Total', '', '', '', 
        f'=SUM(E5:E{totals_row_index - 1})', 
        f'=SUM(F5:F{totals_row_index - 1})', 
        current_btc_price, 
        f'=SUM(H5:H{totals_row_index - 1})', 
        f'=SUM(I5:I{totals_row_index - 1})', 
        f'=SUM(J5:J{totals_row_index - 1})', 
        f'=SUM(K5:K{totals_row_index - 1})'
    ]
    values.append(totals_row)
    
    # Calculate formulas for Current Value and Gain/Loss for each data row.
    # (Assumes data rows start at row 5; adjust the offset if needed.)
    current_value_formulas = [f'=E{row + 5}*$G${totals_row_index}' for row in range(len(data))]
    gain_loss_formulas = [f'=J{row + 5}-H{row + 5}' for row in range(len(data))]

    for row, formula in zip(data.itertuples(index=True), current_value_formulas):
        values[row.Index + 4].append(formula)
    for row, formula in zip(data.itertuples(index=True), gain_loss_formulas):
        values[row.Index + 4].append(formula)
    
    # Unmerge all cells in the range where the earnings sheet will be updated.
    # This ensures that any merged cells—including those in the last data row—are unmerged.
    sheet.batchUpdate(
        spreadsheetId=SHEET_ID,
        body={
            "requests": [
                {
                    "unmergeCells": {
                        "range": {
                            "sheetId": earnings_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": len(values),  # Unmerge all rows in the updated range
                            "startColumnIndex": 0,
                            "endColumnIndex": 11         # Earnings sheet has 11 columns
                        }
                    }
                }
            ]
        }
    ).execute()
    
    # Clear and update
    service.spreadsheets().values().clear(
        spreadsheetId=SHEET_ID,
        range='Earnings!A1:F',
        body={}
    ).execute()

    # Update values
    update_body = {'values': values}
    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range='Earnings!A1',
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

def update_sheet_payouts(data):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_CREDS, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    
    # Retrieve the sheetId for the "Payouts" sheet so that formatting only applies there
    payouts_sheet_id = None
    spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    for sheet in spreadsheet.get("sheets", []):
        if sheet["properties"]["title"] == "Payouts":
            payouts_sheet_id = sheet["properties"]["sheetId"]
            break
    if payouts_sheet_id is None:
        # If no "Payouts" sheet exists, create one.
        add_sheet_request = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": "Payouts",
                            "gridProperties": {
                                "rowCount": 1000,
                                "columnCount": 26
                            }
                        }
                    }
                }
            ]
        }
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID,
            body=add_sheet_request
        ).execute()
        payouts_sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
        print("Created new 'Payouts' sheet with sheetId:", payouts_sheet_id)
    
    # Clean data: replace NaN with empty strings and remove trailing semicolons from text values.
    data = data.fillna('')
    for col in data.select_dtypes(include=['object']).columns:
        data[col] = data[col].apply(lambda x: x.rstrip(';') if isinstance(x, str) else x)

    # Convert the 'Time' column to datetime if it exists (needed for historical BTC price lookup)
    if 'Time' in data.columns:
        data['Time'] = pd.to_datetime(data['Time'], errors='coerce')

    # Compute cost basis (USD) for each payout row if the payout amount column exists.
    # Assumes the CSV has a column named "Payout (BTC)" containing the payout amount in BTC.
    if "Amount (BTC)" in data.columns:
        data["Cost Basis (USD)"] = data.apply(
            lambda row: float(row["Amount (BTC)"]) * get_historical_price(row["Time"])
                        if row["Amount (BTC)"] not in ['', None] else '',
            axis=1
        )
    else:
        data["Cost Basis (USD)"] = ''

    # Reorder the DataFrame columns so that "Cost Basis (USD)" is inserted as the 5th column (index 4)
    cols = list(data.columns)
    if "Cost Basis (USD)" in cols:
        cols.remove("Cost Basis (USD)")
        cols.insert(4, "Cost Basis (USD)")
        data = data[cols]

    # Compute current BTC price to use for gain/loss calculation
    try:
        current_btc_price_float = get_historical_price(pd.Timestamp.now())
    except Exception as e:
        current_btc_price_float = None

    # Compute Gain/Loss (USD) for each payout row using:
    # Gain/Loss = Amount (BTC) * (current BTC price - historical BTC price)
    if "Amount (BTC)" in data.columns and current_btc_price_float:
        data["Gain/Loss (USD)"] = data.apply(
            lambda row: float(row["Amount (BTC)"]) * (current_btc_price_float - get_historical_price(row["Time"]))
                        if row["Amount (BTC)"] not in ['', None] else '',
            axis=1
        )
    else:
        data["Gain/Loss (USD)"] = ''

    # Reorder the DataFrame columns so that "Gain/Loss (USD)" is inserted as the 6th column (index 5)
    cols = list(data.columns)
    if "Gain/Loss (USD)" in cols:
        cols.remove("Gain/Loss (USD)")
        cols.insert(5, "Gain/Loss (USD)")
        data = data[cols]

    # Format the 'Time' column as a string for the sheet display
    if 'Time' in data.columns:
        data['Time'] = data['Time'].dt.strftime('%m/%d/%y %H:%M:%S')

    # Get current BTC price safely
    try:
        current_btc_price = get_historical_price(pd.Timestamp.now()) or ''
    except:
        current_btc_price = ''
    current_btc_price_formatted = f'${current_btc_price:,.2f}' if current_btc_price else ''
    
    # Get current timestamp in human-readable format
    current_timestamp = datetime.now().strftime('%B %d, %Y %I:%M %p')
    
    # Create header rows
    report_header_row = [f'Report as of: {current_timestamp}', '', '', '', '', '', '', '', '', '', '']
    price_header_row = [f'BTC Price: {current_btc_price_formatted}', '', '', '', '', '', '', '', '', '', '']
    empty_row = ['', '', '', '', '', '', '', '', '', '', '']

    # Use the payouts CSV's header row as the table header row
    payouts_headers = list(data.columns)

    # Combine header rows with the data rows
    values = [report_header_row, price_header_row, empty_row, payouts_headers] + data.values.tolist()
    
    # Calculate the 1-indexed row number where the totals row will go.
    totals_row_index = len(values) + 1  
    num_cols = len(payouts_headers)

    # Initialize totals row with empty strings and set first cell to "Total"
    totals_row = ["" for _ in range(num_cols)]
    totals_row[0] = "Total"

    # Data rows start at row 5 (after 4 header rows)
    start_data_row = 5
    end_data_row = totals_row_index - 1

    # Helper function to convert a column number (1-indexed) to its spreadsheet letter.
    def col_letter(n):
        string = ""
        while n:
            n, remainder = divmod(n - 1, 26)
            string = chr(65 + remainder) + string
        return string

    # For specific numeric columns, add SUM formulas.
    for i, header in enumerate(payouts_headers):
        if header in ["Amount (BTC)", "Cost Basis (USD)", "Gain/Loss (USD)"]:
            col = col_letter(i + 1)
            totals_row[i] = f"=SUM({col}{start_data_row}:{col}{end_data_row})"

    values.append(totals_row)
    
    # Clear existing data in the "Payouts" sheet (ensure that a sheet named 'Payouts' exists)
    service.spreadsheets().values().clear(
        spreadsheetId=SHEET_ID,
        range='Payouts!A1:Z',
        body={}
    ).execute()

    # Update the "Payouts" sheet with header rows, data rows, and totals row
    update_body = {'values': values}
    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range='Payouts!A1',
        valueInputOption='USER_ENTERED',
        body=update_body
    ).execute()

    # Unmerge all cells in the updated range on the Payouts sheet.
    service.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={
            "requests": [
                {
                    "unmergeCells": {
                        "range": {
                            "sheetId": payouts_sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": len(values),
                            "startColumnIndex": 0,
                            "endColumnIndex": num_cols
                        }
                    }
                }
            ]
        }
    ).execute()

    # Merge the first 4 cells of the totals row and apply bold text with right alignment on the Payouts sheet.
    service.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={
            "requests": [
                {
                    "mergeCells": {
                        "range": {
                            "sheetId": payouts_sheet_id,
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
                        "range": {
                            "sheetId": payouts_sheet_id,
                            "startRowIndex": totals_row_index - 1,
                            "endRowIndex": totals_row_index
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {"bold": True},
                                "horizontalAlignment": "RIGHT"
                            }
                        },
                        "fields": "userEnteredFormat(textFormat,horizontalAlignment)"
                    }
                }
            ]
        }
    ).execute()

    # Add conditional formatting rules for the Gain/Loss (USD) column in the Payouts sheet.
    # This applies to the column at index 5 (i.e. the 6th column).
    service.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={
            "requests": [
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": payouts_sheet_id,
                                "startRowIndex": 4,
                                "endRowIndex": totals_row_index,
                                "startColumnIndex": 5,
                                "endColumnIndex": 6
                            }],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_LESS",
                                    "values": [{"userEnteredValue": "0"}]
                                },
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
                            "ranges": [{
                                "sheetId": payouts_sheet_id,
                                "startRowIndex": 4,
                                "endRowIndex": totals_row_index,
                                "startColumnIndex": 5,
                                "endColumnIndex": 6
                            }],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_GREATER",
                                    "values": [{"userEnteredValue": "0"}]
                                },
                                "format": {
                                    "textFormat": {"foregroundColor": {"red": 0.0, "green": 0.8, "blue": 0.0}}
                                }
                            }
                        }
                    }
                }
            ]
        }
    ).execute()

def main():
    driver = None
    try:
        driver = setup_driver()
        print(f"Checking data at {datetime.now()}")
        df = get_ocean_data(driver)
        if df is not None:  # Only update if we got earnings data
            update_sheet(df)
            print("Earnings data updated successfully")
            
        # New: Fetch and update payouts data
        payouts_df = get_ocean_payouts(driver)
        if payouts_df is not None:
            update_sheet_payouts(payouts_df)
            print("Payouts data updated successfully")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    print(f"Starting Ocean Mining tracker at {datetime.now()}")
    main()