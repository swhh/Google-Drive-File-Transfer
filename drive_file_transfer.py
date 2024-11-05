from math import ceil
import sys
import time
from connect_service import get_credentials, create_service, JSON_CREDS, USER1_TOKEN, USER2_TOKEN, SCOPES
from find_files import filter_files, search_files
from update_files import bulk_share_files, trash_files

NUM_YEARS = 2 # default min age of files
FILE_PATTERNS = ['DRAFT', 'Technical Narrative', 'FY2', '202'] # default file patterns
FILE_REGEX = r'^FY\d{2}_[A-Za-z0-9\s]+_[A-Za-z0-9\s]+_\d{8}.*' # regex to match file names following the format FYY_<report type>_<company name>_<date>


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


def main(file_patterns, file_regex, age_in_years=None):
  """Transfer files from one Google Drive account to another 
  using file_patterns, file_regex and age_in_years to select files to transfer"""
  creds_user1 = get_credentials(JSON_CREDS, USER1_TOKEN, SCOPES)
  creds_user2 = get_credentials(JSON_CREDS, USER2_TOKEN, SCOPES)
    
  try:
        # Create service for both users
    service_user1 = create_service(creds=creds_user1)
    service_user2 = create_service(creds=creds_user2)

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

  