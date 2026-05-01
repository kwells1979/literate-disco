import os
import requests
from icalendar import Calendar, Event
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
import recurring_ical_events

SOURCE_ICS = os.environ.get("ICS_URL")
if not SOURCE_ICS:
    raise ValueError("ICS_URL environment variable not set")

OUTPUT_FILE = "today.ics"
BRUSSELS_TZ = ZoneInfo("Europe/Brussels")
LONDON_TZ = ZoneInfo("Europe/London")

now = datetime.now(LONDON_TZ)
today = now.date()

# Today + next 6 days = 7 days total
start_of_period = datetime.combine(today, time.min).replace(tzinfo=LONDON_TZ)
end_of_period = start_of_period + timedelta(days=7)

response = requests.get(SOURCE_ICS, timeout=30)
response.raise_for_status()

source_cal = Calendar.from_ical(response.content)
new_cal = Calendar()

# Copy calendar-level metadata
for key, value in source_cal.items():
    if key != "VEVENT":
        new_cal.add(key, value)

# Expand recurring events and filter to the next 7 days
events = recurring_ical_events.of(source_cal).between(start_of_period, end_of_period)

for component in events:
    event_start = component.get("dtstart").dt
    event_end = component.get("dtend").dt if component.get("dtend") else event_start

    # Handle all-day events
    if isinstance(event_start, date) and not isinstance(event_start, datetime):
        event_start = datetime.combine(event_start, time.min).replace(tzinfo=LONDON_TZ)

    if isinstance(event_end, date) and not isinstance(event_end, datetime):
        event_end = datetime.combine(event_end, time.max).replace(tzinfo=LONDON_TZ)

    # Handle missing timezone, assume Brussels
    if event_start.tzinfo is None:
        event_start = event_start.replace(tzinfo=BRUSSELS_TZ)

    if event_end.tzinfo is None:
        event_end = event_end.replace(tzinfo=BRUSSELS_TZ)

    # Convert to UK local time, handles GMT/BST automatically
    event_start = event_start.astimezone(LONDON_TZ)
    event_end = event_end.astimezone(LONDON_TZ)

    new_event = Event()

    # Copy fields except ones we override or strip
    for key in component.keys():
        if key in ("DTSTART", "DTEND", "ATTENDEE", "VALARM", "DESCRIPTION", "CLASS"):
            continue
        new_event.add(key, component.get(key))

    # Set cleaned times
    new_event.add("dtstart", event_start)
    new_event.add("dtend", event_end)

    new_cal.add_component(new_event)

with open(OUTPUT_FILE, "wb") as f:
    f.write(new_cal.to_ical())

print(f"today.ics generated — {len(events)} event(s) from {today} for 7 days")