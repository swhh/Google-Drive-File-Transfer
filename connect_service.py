import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

JSON_CREDS = "credentials.json"
USER1_TOKEN = "token_user1.json"
USER2_TOKEN = "token_user2.json"
# If modifying the scope, delete the token.json files.
SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_credentials(credentials_file, token_file, scopes):
    """Get valid user credentials from storage"""
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, scopes
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, "w") as token:
            token.write(creds.to_json())
    return creds

def create_service(creds):
    return build("drive", "v3", credentials=creds)