import os.path
import re
import calendar
from datetime import datetime
import pandas as pd
from flask import Flask, request, jsonify

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

app = Flask(__name__)

# --------------------------
# 🔐 Secure API Key (set this securely in environment)
API_KEY = "Test"
# --------------------------

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Use fixed month or current
current_month = 4
# current_month = datetime.today().month
current_month_name = calendar.month_name[current_month]
current_year = datetime.today().year

def get_service():
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
    return build('gmail', 'v1', credentials=creds)

def extract_payment_amount(snippet):
    match = re.search(r'Total price Rs\.(\d+)', snippet)
    return int(match.group(1)) if match else 0

def list_emails_from_sender(sender_email):
    service = get_service()

    query = f'from:{sender_email} after:2025/{current_month}/01 before:2025/{current_month + 1}/01'

    results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
    messages = results.get('messages', [])

    if not messages:
        return [], 0

    data = []

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_data['payload'].get('headers', [])
        snippet = msg_data.get('snippet', '')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')

        if f"Yango ride report for {current_month_name}" in subject:
            amount = extract_payment_amount(snippet)
            date = subject.split("Yango ride report for")[1].strip()
            parsed_date = datetime.strptime(date, "%B %d, %Y").strftime("%d-%B-%Y")
            data.append({
                "Date": parsed_date,
                "Snippet": snippet,
                "Amount": amount
            })

    df = pd.DataFrame(data)
    df.to_excel(f"{current_month_name}.xlsx", index=False)

    total_payment = df['Amount'].sum()
    return data, total_payment


@app.route('/api/yango-summary', methods=['GET'])
def yango_summary():
    key = request.args.get('key')
    if key != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    sender_email = "no-reply@yango.com"
    data, total_amount = list_emails_from_sender(sender_email)
    return jsonify({
        'total_rides': int(len(data)),
        'total_amount': int(total_amount),
        'month': str(current_month_name),
        'year': int(2025)
    })


# --------------------------

if __name__ == '__main__':
    app.run(debug=True)
