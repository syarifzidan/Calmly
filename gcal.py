from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def add_event(title, date, time, duration):
    service = get_calendar_service()

    # Build start and end times
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
    # print(f"Event created: {created.execute().get('htmlLink')}")
