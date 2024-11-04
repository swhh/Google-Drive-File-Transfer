from datetime import datetime, timedelta, timezone
from math import ceil
import os.path
import re
import sys
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


NUM_YEARS = 2 # default min age of files
FILE_PATTERNS = ['DRAFT', 'Technical Narrative', 'FY2', '202'] # default file patterns
FILE_REGEX = r'^FY\d{2}_[A-Za-z0-9\s]+_[A-Za-z0-9\s]+_\d{8}.*' # regex to match file names following the format FYY_<report type>_<company name>_<date>
JSON_CREDS = "credentials.json"
USER1_TOKEN = "token_user1.json"
USER2_TOKEN = "token_user2.json"
# If modifying the scope, delete the token.json files.
SCOPES = ["https://www.googleapis.com/auth/drive"]


def bulk_share_files(source_service, dest_email, file_ids, batch_size=100):
    """Share files with destination"""
    def callback(request_id, response, exception):
        if exception:
            print(f"Error sharing file {request_id}: {exception}")
        else:
            print(f"Shared file {request_id}")
    for i in range(ceil(len(file_ids) / batch_size)):     
      batch = source_service.new_batch_http_request(callback=callback)
      for file_id in file_ids[i * batch_size: (i + 1) * batch_size]:
          permission = {
              'type': 'user',
              'role': 'writer',
              'emailAddress': dest_email
          }
          batch.add(source_service.permissions().create(
              fileId=file_id,
              body=permission,
              fields='id',
              sendNotificationEmail=False
          ))
      batch.execute()

def bulk_copy_files(dest_service, file_ids, batch_size=100, delay_sec=0.5):
    """Copy files to destination"""
    def callback(request_id, response, exception):
        if exception:
            print(f"Error copying file {request_id}: {exception}")
        else:
            print(f"Copied file {request_id}: New ID {response['id']}")

    for i in range(ceil(len(file_ids)/ batch_size)):
      time.sleep(delay_sec) # to stop batch timeouts
      try:    
        batch = dest_service.new_batch_http_request(callback=callback)
        for file_id in file_ids[i * batch_size: (i + 1) * batch_size]:
            batch.add(dest_service.files().copy(fileId=file_id, body={}))
        batch.execute()
      except Exception as e:
         print(e)

def bulk_transfer_files(source_service, dest_service, file_ids, trash=False):
   """Transfer files from source to destination"""
   dest_email = dest_service.about().get(fields='user').execute()['user']['emailAddress']
   bulk_share_files(source_service, dest_email, file_ids)
   bulk_copy_files(dest_service, file_ids)
   print('Finished transferring')
   if trash:
      trash_files(source_service, file_ids)
      print('Finished trashing files')

def search_files(service, file_patterns, age_in_years=None, page_lim=10):
    """Find files from service that contain at least one pattern from file_patterns and are at least age_in_years old"""
    query = ' or '.join(f"name contains '{file_pattern}'" for file_pattern in file_patterns)
    page_token = None
    all_files = []

    if age_in_years:
        time_stamp = (datetime.now(timezone.utc) - timedelta(days=365 * age_in_years)).strftime('%Y-%m-%dT%H:%M:%S%z')
        query = '(' + query + ')'
        query += f" and createdTime < '{time_stamp}'" # get files that were created over age_in_years ago

    for _ in range(page_lim):
      results = service.files().list(q=query, pageSize=1000, pageToken=page_token, fields="nextPageToken, files(id, name)").execute()
      files = results.get('files', [])
      if files:
        all_files.extend(files)
      page_token = results.get('nextPageToken', None)
      if not page_token or not files:
         break   
          
    return all_files


def filter_files(files, regex_patterns):
  """Filter files to find those that match regex_patterns"""
  pattern = re.compile(regex_patterns)
  match = pattern.match
  return filter(lambda x: match(x['name']), files)

def trash_files(service, files):
  """Trash all files from service account"""
  body_value = {'trashed': True}
  for file in files:
    try:
      service.files().update(fileId=file['id'], body=body_value).execute()
    except:
      print(f"Could not trash {file['id']}: {file['name']}")


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



def main(file_patterns, file_regex, age_in_years=None):
  """Transfer files from one Google Drive account to another 
  using file_patterns, file_regex and age_in_years to select files to transfer"""
  creds_user1 = get_credentials(JSON_CREDS, USER1_TOKEN, SCOPES)
  creds_user2 = get_credentials(JSON_CREDS, USER2_TOKEN, SCOPES)
    
  try:
        # Create service for both users
    service_user1 = build("drive", "v3", credentials=creds_user1)
    service_user2 = build("drive", "v3", credentials=creds_user2)

    files = search_files(service_user1, file_patterns, age_in_years=age_in_years) # get files from user1 account
    files = filter_files(files, file_regex) # filter files to match regex
    bulk_transfer_files(service_user1, service_user2, [file['id'] for file in files], batch_size=10) # share and copy files to user2 account
  except Exception as e:
    print(f"An error occurred: {e}")


if __name__ == "__main__":
  args = sys.argv
  file_patterns = FILE_PATTERNS
  file_regex = FILE_REGEX
  age_in_years = NUM_YEARS
  if len(args) >= 3:
     _, file_patterns, file_regex = args[:3]
  if len(args) == 4:
     age_in_years = int(args[3])
  main(file_patterns, file_regex, age_in_years=age_in_years)

  