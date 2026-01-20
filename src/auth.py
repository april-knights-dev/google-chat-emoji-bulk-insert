"""OAuth 2.0 authentication module for Google Chat API."""

import os
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google Chat API scope for custom emojis
SCOPES = ['https://www.googleapis.com/auth/chat.customemojis']


def get_credentials(credentials_path: str = 'credentials.json', token_path: str = 'token.pickle') -> Credentials:
    """
    Get valid user credentials for Google Chat API.

    Args:
        credentials_path: Path to the OAuth client credentials JSON file
        token_path: Path to store/load the user's access token

    Returns:
        Valid Credentials object

    Raises:
        FileNotFoundError: If credentials.json is not found
    """
    creds = None
    token_file = Path(token_path)

    # Load existing token if available
    if token_file.exists():
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, initiate OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(credentials_path).exists():
                raise FileNotFoundError(
                    f"Credentials file not found: {credentials_path}\n"
                    "Please download OAuth client credentials from Google Cloud Console:\n"
                    "1. Go to https://console.cloud.google.com/apis/credentials\n"
                    "2. Create an OAuth 2.0 Client ID (Desktop application)\n"
                    "3. Download the JSON and save as 'credentials.json'"
                )

            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for future runs
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
        print(f"Token saved to {token_path}")

    return creds
