import requests
import json
import re
from datetime import date, timedelta, datetime

today = date.today()


def extract_events(text):
    prompt = f"""You are a text to calendar assistant. Extract a calendar event from the following text and return ONLY a JSON, no explanation, no markdown. You are given access to today's date below, if the extracted text use time relative expressions use today's date to figure out when the event takes place (for example if it says tomorrow the date becomes Today's date + 1 or if its next week then Today's date + 7) if there is no date in Text assume the date is Today's date. If there is no end_time set end_time as 23:00. the event should have: title , date (YYYY-MM-DD), start_time (HH:MM), and end_time (HH:MM).
Today's date: {today}
Text: {text}

JSON:"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.2", "prompt": prompt, "stream": False},
    )

    raw = response.json()["response"]
    return clean_json(raw)


def clean_json(raw):
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        events = json.loads(raw)
        # print("succesfully parsed JSON, raw output was:")
        # print(raw)
        # print(type(raw))
        # print(events)
        # print(type(events))

        time1_str = events["start_time"]
        time2_str = events["end_time"]
        FMT = "%H:%M"

        # Convert strings to datetime objects using a base date (e.g., min date)
        # This is necessary to subtract them
        tdelta = datetime.strptime(time2_str, FMT) - datetime.strptime(time1_str, FMT)
        total_minutes = int(tdelta.total_seconds() / 60)
        # print(f"Time difference (timedelta object): {tdelta}")
        # print(f"Total minutes: {total_minutes}")
        events["duration"] = total_minutes
        del events["end_time"]
        # print(f"new events: {events}")
        return events
    except json.JSONDecodeError:
        print("Couldn't parse JSON, raw output was:")
        print(raw)
        return []


# testing
# sample_text = "minggu depan utspnya di lab ssmi 3 jam 9:00-11:30,"
# events = extract_events(sample_text)


# for event in events:
#     print(f"{event} : {events[event]}")
