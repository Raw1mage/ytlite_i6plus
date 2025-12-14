import os
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
token_path = '/var/mobile/Documents/yt_lite/token.json'

print(f'Checking {token_path}...')
if os.path.exists(token_path):
    print('File exists.')
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        print(f'Credentials loaded: {creds}')
        print(f'Valid: {creds.valid}')
        print(f'Expired: {creds.expired}')
        if not creds.valid:
            print('Trying refresh...')
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            print('Refresh success.')
    except Exception as e:
        print(f'ERROR: {e}')
else:
    print('File NOT found.')
