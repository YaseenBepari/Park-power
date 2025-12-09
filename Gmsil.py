from __future__ import print_function
import os.path
import base64
import email
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """Authenticate and return a Gmail service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def create_message(sender, to, subject, message_text):
    """Create a message for an email."""
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes())
    return {'raw': raw_message.decode()}

def send_message(service, user_id, message):
    """Send an email message."""
    try:
        sent_message = service.users().messages().send(userId=user_id, body=message).execute()
        print(f"Message Id: {sent_message['id']}")
        return sent_message
    except Exception as error:
        print(f"An error occurred: {error}")

def get_emails(service, max_results=10):
    """Fetch emails from the user's inbox."""
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])

    if not messages:
        print('No messages found.')
    else:
        print(f'{len(messages)} messages retrieved:')
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = msg_data.get('payload', {})
            headers = payload.get('headers', [])

            email_data = {}
            for header in headers:
                if header['name'] == 'From':
                    email_data['From'] = header['value']
                if header['name'] == 'Subject':
                    email_data['Subject'] = header['value']
                if header['name'] == 'Date':
                    email_data['Date'] = header['value']

            snippet = msg_data.get('snippet', '')
            email_data['Snippet'] = snippet

            print("="*50)
            print(f"From: {email_data.get('From')}")
            print(f"Subject: {email_data.get('Subject')}")
            print(f"Date: {email_data.get('Date')}")
            print(f"Snippet: {email_data.get('Snippet')}")
            print("="*50)

if __name__ == '__main__':
    # Send Email
    sender = "yaseenbepari2002@gmail.com"
    to = "park.and.power.project@gmail.com"
    subject = "Departure of the Park and Power Project"
    message_text = "This is a test email message sent from Gmail API!"
    
    service = authenticate_gmail()
    message = create_message(sender, to, subject, message_text)
    send_message(service, 'me', message)
    
    # Fetch Emails
    get_emails(service, max_results=5)  # Fetch 5 emails
