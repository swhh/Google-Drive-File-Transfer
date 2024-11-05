from datetime import datetime, timedelta, timezone
import re

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
