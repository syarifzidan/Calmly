import requests
import json
import re
import base64
from datetime import date
from time_logic import update_duration
from PIL import Image
import pytesseract

today = date.today()

VISION_MODEL = "moondream"
TEXT_MODEL = "llama3.2"

PROMPT_TEMPLATE = """You are a text to calendar assistant. Extract a calendar event from the following text and return ONLY a JSON, no explanation, no markdown. You are given access to today's date below, if the extracted text use time relative expressions use today's date to figure out when the event takes place (for example if it says tomorrow the date becomes Today's date + 1 or if its next week then Today's date + 7) if there is no date in Text assume the date is Today's date. If there is no end_time set end_time as 23:00. the event should have: title , date (YYYY-MM-DD), start_time (HH:MM), and end_time (HH:MM).
Today's date: {today}
Text: {text}

JSON:"""

IMAGE_PROMPT = """You are a text to calendar assistant. Look at this image — it contains a chat or message about an event. Extract the calendar event details and return ONLY a JSON, no explanation, no markdown. You are given access to today's date below, if the text uses relative expressions (e.g. "tomorrow", "next week") use today's date to compute the real date. If there is no date, assume today's date. If there is no end_time, set it to 23:00. The event should have: title, date (YYYY-MM-DD), start_time (HH:MM), and end_time (HH:MM).
Today's date: {today}

JSON:"""


def call_ollama(payload):
    """Call Ollama API and return the response text, with clear error messages."""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=payload,
    )

    result = response.json()

    # Print full response for debugging
    print("=== Ollama raw response ===")
    print(json.dumps(result, indent=2))
    print("===========================")

    if "error" in result:
        raise ValueError(f"Ollama error: {result['error']}")

    if "response" not in result:
        raise ValueError(
            f"Unexpected Ollama response format. Keys: {list(result.keys())}"
        )

    return result["response"]


def extract_events(text):
    prompt = PROMPT_TEMPLATE.format(today=today, text=text)
    raw = call_ollama({"model": TEXT_MODEL, "prompt": prompt, "stream": False})
    return clean_json(raw)


# Point to your Tesseract install path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_events_from_image(image_path):
    # Extract text from image, using Indonesian + English language data
    text = pytesseract.image_to_string(Image.open(image_path), lang="ind+eng")
    print(f"OCR extracted text:\n{text}")
    # Reuse the existing text pipeline
    return extract_events(text)


def clean_json(raw):
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        events = json.loads(raw)
        update_duration(events)
        return events
    except json.JSONDecodeError:
        print("Couldn't parse JSON, raw output was:")
        print(raw)
        return []
