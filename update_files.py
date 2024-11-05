from math import ceil
import sys

TRASH = False # default do not trash


def trash_files(service, files):
  """Trash all files from service account"""
  body_value = {'trashed': True}
  for file in files:
    try:
      service.files().update(fileId=file['id'], body=body_value).execute()
    except:
      print(f"Could not trash {file['id']}: {file['name']}")


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


def main(file_patterns, trash=False):
   creds_user = cs.get_credentials(cs.JSON_CREDS, cs.USER1_TOKEN, cs.SCOPES)
   service_user = cs.create_service(creds_user)

   files = ff.search_files(service_user, file_patterns=file_patterns)
   print(f'There are {len(files)} files')
   print(f'The first ten file names are:', ' '.join(file['name'] for file in files[:10]))
   if bool(trash):
      print('trashing files')
      trash_files(service_user, files)
      print('finished trashing files')

if __name__ == '__main__':
   import connect_service as cs
   import find_files as ff
   args = sys.argv
   file_patterns = []
   trash = TRASH
   if len(args) > 2:
      trash = args[1]
      file_patterns = args[2:]
   main(file_patterns, trash=False)
  

   

   

