from datetime import timedelta, datetime


def get_time_dif(start_time, end_time):
    time1_str = start_time
    time2_str = end_time
    FMT = "%H:%M"

    # Convert strings to datetime objects using a base date (e.g., min date)
    # This is necessary to subtract them
    tdelta = datetime.strptime(time2_str, FMT) - datetime.strptime(time1_str, FMT)
    total_minutes = int(tdelta.total_seconds() / 60)
    return total_minutes
def update_duration(events):
    total_minutes = get_time_dif(events["start_time"], events["end_time"])
    events["duration"] = total_minutes

