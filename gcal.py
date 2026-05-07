from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Always resolve paths relative to this file, not the working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")


def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def add_event(title, date, time, duration):
    service = get_calendar_service()

    start = f"{date}T{time}:00"
    from datetime import datetime, timedelta

    end_dt = datetime.fromisoformat(start) + timedelta(minutes=duration)
    end = end_dt.isoformat()

    event = {
        "summary": title,
        "start": {"dateTime": start, "timeZone": "Asia/Jakarta"},
        "end": {"dateTime": end, "timeZone": "Asia/Jakarta"},
    }

    created = service.events().insert(calendarId="primary", body=event)
    return created
