import os
import requests
from icalendar import Calendar, Event
from datetime import datetime, date, time
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

start_of_day = datetime.combine(today, time.min).replace(tzinfo=LONDON_TZ)
end_of_day = datetime.combine(today, time.max).replace(tzinfo=LONDON_TZ)

response = requests.get(SOURCE_ICS)
response.raise_for_status()

source_cal = Calendar.from_ical(response.content)
new_cal = Calendar()

for key, value in source_cal.items():
    if key != "VEVENT":
        new_cal.add(key, value)

# recurring_ical_events expands RRULE series and returns only the
# single occurrence that falls within today's window.
events = recurring_ical_events.of(source_cal).between(start_of_day, end_of_day)

for component in events:
    event_start = component.get("dtstart").dt
    event_end = component.get("dtend").dt if component.get("dtend") else event_start

    # All-day events come through as date objects — treat as London midnight
    if isinstance(event_start, date) and not isinstance(event_start, datetime):
        event_start = datetime.combine(event_start, time.min).replace(tzinfo=LONDON_TZ)
    if isinstance(event_end, date) and not isinstance(event_end, datetime):
        event_end = datetime.combine(event_end, time.max).replace(tzinfo=LONDON_TZ)

    # Naive datetimes mean the source calendar has no tz info —
    # assume Brussels since that's where they're created.
    if event_start.tzinfo is None:
        event_start = event_start.replace(tzinfo=BRUSSELS_TZ)
    if event_end.tzinfo is None:
        event_end = event_end.replace(tzinfo=BRUSSELS_TZ)

    # Convert everything to London time (handles GMT/BST automatically)
    event_start = event_start.astimezone(LONDON_TZ)
    event_end = event_end.astimezone(LONDON_TZ)

    new_event = Event()

    # Copy all fields except the ones we're setting manually or stripping out
    for key in component.keys():
        if key in ("DTSTART", "DTEND", "ATTENDEE", "VALARM", "DESCRIPTION", "CLASS"):
            continue
        new_event.add(key, component.get(key))

    # Add the converted times
    new_event.add("dtstart", event_start)
    new_event.add("dtend", event_end)

    new_cal.add_component(new_event)

with open(OUTPUT_FILE, "wb") as f:
    f.write(new_cal.to_ical())

print(f"today.ics generated — {len(events)} event(s) for {today}")
