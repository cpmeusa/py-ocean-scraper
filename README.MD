# BTC Mining Share Log Automation

This project automates the process of extracting BTC mining share log data from a website, calculating cost basis and gain/loss, and updating a Google Sheet with the formatted data.

## Prerequisites

Before running the script, ensure you have the following:

- Python 3.x installed
- Google Chrome browser installed
- Google Cloud project set up with Google Sheets API enabled
- Service account credentials JSON file for authentication

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/your-repository.git
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

## Configuration

1. Create a copy of the `config_sample.py` file and rename it to `config.py`.

2. Update the `config.py` file with the necessary configuration details:
   - `SERVICE_ACCOUNT_CREDS`: Replace the placeholders with your actual service account credentials.
   - `MINER_ADDRESS`: Your Bitcoin address for mining.
   - `SHEET_ID`: ID of the Google Sheet to update.
   - `CHECK_INTERVAL`: Interval for checking the share log (in seconds).
   - Optional configuration:
     - `DOWNLOADS_PATH`: Customize the download location (default is "~/Downloads").
     - `MAX_DOWNLOAD_WAIT`: Maximum wait time for downloads (default is 30 seconds).

## BTC Price Cache

The script utilizes a caching mechanism to store historical BTC prices and avoid making unnecessary API requests. The cached prices are stored in a JSON file named `btc_price_cache.json`.

- When the script encounters a new timestamp, it fetches the corresponding BTC price from the API and stores it in the cache file.
- If the script encounters a timestamp that already exists in the cache, it retrieves the price from the cache file instead of making an API request.
- The cache file is automatically created and updated as the script runs.

## Usage

1. Ensure that you have completed the installation and configuration steps.

2. Run the script:
   ```
   python main.py
   ```

   The script will automatically download the share log, extract the data, calculate cost basis and gain/loss, and update the Google Sheet.

3. To run the script continuously, you can set up a cron job or a task scheduler to execute the script at regular intervals.

## Building an Executable

If you want to build an executable file for the script, you can use PyInstaller. Run the following command:
```
pyinstaller --onefile main.py
```

This will generate an executable file in the `dist` directory.

## Troubleshooting

- If the script fails to log in or navigate to the share log page, check the website's structure and update the XPaths in the script accordingly.
- If the Google Sheet is not updating correctly, ensure that the service account has the necessary permissions to access and modify the sheet.
- If the executable file is not running correctly, ensure that all the required dependencies are properly included during the PyInstaller build process.

## License

This project is licensed under the [MIT License](LICENSE).

Feel free to customize and enhance the script based on your specific requirements.
