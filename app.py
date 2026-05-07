from gcal import add_event
from llm import extract_events, extract_events_from_image
from time_logic import update_duration
import os
import uuid

from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

events = {}
event_text = ""
link = ""


@app.route("/", methods=["GET", "POST"])
def index():
    global events
    global event_text
    if request.method == "POST":
        image_file = request.files.get("event_image")
        raw_text = request.form.get("raw_event_text", "").strip()

        if image_file and image_file.filename:
            ext = os.path.splitext(image_file.filename)[1].lower()
            tmp_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}{ext}")
            image_file.save(tmp_path)
            # extract_events_from_image now returns (events_dict, ocr_text)
            events, event_text = extract_events_from_image(tmp_path)
            os.remove(tmp_path)
        elif raw_text:
            event_text = raw_text
            events = extract_events(event_text)
        else:
            return render_template(
                "index.html", error="Please enter text or upload an image."
            )

        return redirect(url_for("edit"))

    return render_template("index.html")


@app.route("/edit", methods=["GET", "POST"])
def edit():
    global events
    global link
    if request.method == "POST":
        new_title = request.form.get("new_title")
        new_date = request.form.get("new_date")
        new_start_time = request.form.get("new_start_time")
        new_end_time = request.form.get("new_end_time")

        if new_title:
            events["title"] = new_title
        if new_date:
            events["date"] = new_date
        if new_start_time:
            events["start_time"] = new_start_time
        if new_end_time:
            events["end_time"] = new_end_time
            update_duration(events)

        if request.form.get("finished"):
            del events["end_time"]
            created_event = add_event(
                events["title"],
                events["date"],
                events["start_time"],
                events["duration"],
            )
            link = created_event.execute().get("htmlLink")
            return redirect(url_for("finished"))

    return render_template(
        "edit.html",
        title=events["title"],
        date=events["date"],
        start_time=events["start_time"],
        duration=events["duration"],
        end_time=events["end_time"],
        rawtext=event_text,
    )


@app.route("/finished", methods=["GET", "POST"])
def finished():
    if request.form.get("return"):
        return redirect(url_for("index"))
    return render_template("finished.html", link=link)


if __name__ == "__main__":
    app.run(debug=True)
