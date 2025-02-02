# Changelog

## [1.1.1] - 2025-02-02
### Changed
- Removed interval references from configuration and documentation.
- Updated the README to include instructions on how to create a Google Sheet and retrieve its ID.
- Added automatic creation of separate sheets for **Earnings** and **Payouts**.

## [1.1.0] - 2025-01-27
### Added
- Implemented a BTC price caching mechanism to store historical BTC prices and avoid unnecessary API requests. The cached prices are stored in a JSON file named `btc_price_cache.json`. When the script encounters a new timestamp, it fetches the corresponding BTC price from the API and stores it in the cache file. If the script encounters a timestamp that already exists in the cache, it retrieves the price from the cache file instead of making an API request. The cache file is automatically created and updated as the script runs.

### Fixed
- Resolved an issue where merged cells in the Google Sheet were causing problems when new data was added. The script now unmerges the cells programmatically using the Google Sheets API before updating the data. This ensures that the new data fills the rows correctly without any merging conflicts.

### Changed
- Updated the `README.md` file to include information about the BTC price cache and its functionality.

## [1.0.0] - 2025-01-26
### Added
- Initial release of the BTC Mining Share Log Automation script.
- Automated the process of extracting BTC mining share log data from a website, calculating cost basis and gain/loss, and updating a Google Sheet with the formatted data.
- Implemented configuration options for service account credentials, miner address, sheet ID, and check interval.
- Added error handling and troubleshooting steps in the README file.
