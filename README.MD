# BTC Mining Share Log Automation

This project automates the process of extracting BTC mining share log data from a website, calculating cost basis and gain/loss, and updating a Google Sheet with the formatted data.

## Prerequisites

Before running the script, ensure you have the following:

- Python 3.x installed
- Google Chrome browser installed
- Google Cloud project set up with Google Sheets API enabled
- Service account credentials JSON file for authentication

## Installation

1. Clone the repository or download the script files.

2. Install the required Python packages by running the following command:
   ```
   pip install -r requirements.txt
   ```

3. Place the service account credentials JSON file in the same directory as the script and update the `SERVICE_ACCOUNT_CREDS` variable in the `config.py` file with the path to the credentials file.

## Configuration

1. Update the `config.py` file with the necessary configuration details:
   - `SERVICE_ACCOUNT_CREDS`: Path to the service account credentials JSON file.
   - `SPREADSHEET_ID`: ID of the Google Sheet to update.
   - `RANGE_NAME`: Range name of the sheet to update (e.g., "Sheet1!A1").
   - `USERNAME`: Username for logging into the website.
   - `PASSWORD`: Password for logging into the website.

## Usage

1. Run the `main.py` script using the following command:
   ```
   python main.py
   ```

2. The script will perform the following steps:
   - Launch a Chrome browser and navigate to the login page.
   - Log in using the provided username and password.
   - Navigate to the share log page and extract the data.
   - Fetch historical BTC prices for each timestamp.
   - Calculate cost basis, pool fees cost basis, current value, and gain/loss using formulas.
   - Update the Google Sheet with the formatted data.
   - Apply formatting to the sheet, including date/time format, currency format, and conditional formatting for gain/loss.

3. Once the script finishes executing, the Google Sheet will be updated with the latest share log data and calculations.

## Functionality

The script performs the following main tasks:

1. **Data Extraction**: It uses Selenium to automate the process of logging into the website, navigating to the share log page, and extracting the relevant data from the HTML table.

2. **Data Formatting**: The extracted data is formatted and processed using Pandas. The script applies necessary transformations, such as converting timestamps to a readable format and calculating cost basis and gain/loss using formulas.

3. **Historical BTC Prices**: The script fetches historical BTC prices for each timestamp using an external API. This allows for accurate calculation of cost basis and gain/loss in USD.

4. **Google Sheet Update**: The formatted data is then uploaded to a specified Google Sheet using the Google Sheets API. The script updates the sheet with the latest data and applies formatting, such as date/time format, currency format, and conditional formatting for gain/loss.

5. **Automation**: The script automates the entire process, from data extraction to updating the Google Sheet, eliminating the need for manual intervention.

## Building an Executable

To create a standalone executable file for the script, you can use PyInstaller. Follow these steps:

1. Install PyInstaller by running the following command:
   ```
   pip install pyinstaller
   ```

2. Navigate to the directory containing the `main.py` script.

3. Run the following command to create an executable file:
   ```
   pyinstaller --onefile main.py
   ```

4. The executable file will be generated in the `dist` directory.

## Troubleshooting

- If the script fails to log in or navigate to the share log page, check the website's structure and update the XPaths in the script accordingly.
- If the Google Sheet is not updating correctly, ensure that the service account has the necessary permissions to access and modify the sheet.
- If the executable file is not running correctly, ensure that all the required dependencies are properly included during the PyInstaller build process.

## License

This project is licensed under the [MIT License](LICENSE).

Feel free to customize and enhance the script based on your specific requirements.
