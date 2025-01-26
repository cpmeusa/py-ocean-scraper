# Service account credentials
SERVICE_ACCOUNT_CREDS = {
    "type": "service_account",
    "project_id": "your-project-id",
    "private_key_id": "your-private-key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
    "client_email": "your-client-email",
    "client_id": "your-client-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "your-client-cert-url"
}

# Bitcoin address for mining
MINER_ADDRESS = "your-bitcoin-address"

# ID of the Google Sheet to update
SHEET_ID = "your-sheet-id"

# Interval for checking the share log (in seconds)
CHECK_INTERVAL = 3600  # Check every hour

# Optional configuration
#DOWNLOADS_PATH = "~/Downloads"  # Customize download location
MAX_DOWNLOAD_WAIT = 30 