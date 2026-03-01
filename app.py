from gcal import add_event
from llm import extract_events
from time_logic import update_duration

# TODO: (optional) make the site prettier

# testing
# add_event("Test Event", "2026-03-06", "14:00", 60)


# # sample_text = input()
# events = extract_events(sample_text)
# print("event information:")
# for event in events:
#     print(f"{event} : {events[event]}")


# print("input a number to edit the event:\n1. title\n2. date\n3. start time\n4.duration")
# add_event(events["title"], events["date"], events["start_time"], events["duration"])


from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    global events
    global sample_text
    if request.method == "POST":
        sample_text = request.form["raw_text"]
        events = extract_events(sample_text)
        # created_event = add_event(
        #     events["title"], events["date"], events["start_time"], events["duration"]
        # )
        # return f"Event created: {created_event.execute().get('htmlLink')}"
        print(f"edit url: {url_for('edit')} ")
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
        # new_duration = request.form.get("new_duration")
        new_end_time = request.form.get("new_end_time")
        if new_title:
            events["title"] = new_title
        if new_date:
            events["date"] = new_date
        if new_start_time:
            events["start_time"] = new_start_time
        # if new_duration:
        #     events["duration"] = int(new_duration)
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
        rawtext=sample_text,
    )


@app.route("/finished", methods=["GET", "POST"])
def finished():
    if request.form.get("return"):
        return redirect(url_for("index"))
    return render_template("finished.html", link=link)


if __name__ == "__main__":
    app.run(debug=True)
