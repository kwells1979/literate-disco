import os
import requests
from icalendar import Calendar, Event
from datetime import datetime, date, time
from zoneinfo import ZoneInfo

SOURCE_ICS = os.environ.get("ICS_URL")
if not SOURCE_ICS:
    raise ValueError("ICS_URL environment variable not set")
OUTPUT_FILE = "today.ics"
TZ = ZoneInfo("Europe/London")

now = datetime.now(TZ)
today = now.date()

start_of_day = datetime.combine(today, time.min).replace(tzinfo=TZ)
end_of_day = datetime.combine(today, time.max).replace(tzinfo=TZ)

response = requests.get(SOURCE_ICS)
response.raise_for_status()

source_cal = Calendar.from_ical(response.content)
new_cal = Calendar()

for key, value in source_cal.items():
    if key != "VEVENT":
        new_cal.add(key, value)

for component in source_cal.walk():
    if component.name != "VEVENT":
        continue

    event_start = component.get("dtstart").dt
    event_end = component.get("dtend").dt if component.get("dtend") else event_start

    if isinstance(event_start, date) and not isinstance(event_start, datetime):
        event_start = datetime.combine(event_start, time.min)

    if isinstance(event_end, date) and not isinstance(event_end, datetime):
        event_end = datetime.combine(event_end, time.max)

    if event_start.tzinfo is None:
        event_start = event_start.replace(tzinfo=TZ)

    if event_end.tzinfo is None:
        event_end = event_end.replace(tzinfo=TZ)

    if not (event_start <= end_of_day and event_end >= start_of_day):
        continue

    new_event = Event()

    for key in component.keys():
        if key in ["ATTENDEE", "VALARM", "DESCRIPTION", "CLASS"]:
            continue
        new_event.add(key, component.get(key))

    new_cal.add_component(new_event)

with open(OUTPUT_FILE, "wb") as f:
    f.write(new_cal.to_ical())

print("today.ics generated")
