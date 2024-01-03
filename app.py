import datetime
import os
import sys
import time
import pytz
import requests
from icalendar import Calendar
from PIL import Image, ImageDraw, ImageFont
from waveshare_OLED import OLED_1in5_rgb

picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pic')
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

oled = OLED_1in5_rgb.OLED_1in5_rgb()
oled.Init()

def read_ics_link():
    with open("ics_link.txt", "r") as f:
        return f.readline().strip()

def get_current_event_status(file_path_or_url):
    local_tz = pytz.timezone("America/Toronto")
    now = datetime.datetime.now(local_tz)

    # Fetch ICS file
    headers = {'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}
    if file_path_or_url.startswith("http://") or file_path_or_url.startswith("https://"):
        response = requests.get(file_path_or_url, headers=headers)
        response.raise_for_status()
        cal_content = response.content
    else:
        with open(file_path_or_url, "rb") as f:
            cal_content = f.read()

    cal = Calendar.from_ical(cal_content)

    for event in cal.walk("VEVENT"):
        event_start = event.get("dtstart").dt
        event_end = event.get("dtend").dt
        event_status = event.get("status")

        # Convert dates and datetimes to local timezone and make offset-aware
        if isinstance(event_start, datetime.date) and not isinstance(event_start, datetime.datetime):
            event_start = local_tz.localize(datetime.datetime.combine(event_start, datetime.datetime.min.time()))
        else:
            event_start = event_start.astimezone(local_tz)

        if isinstance(event_end, datetime.date) and not isinstance(event_end, datetime.datetime):
            event_end = local_tz.localize(datetime.datetime.combine(event_end, datetime.datetime.max.time()))
        else:
            event_end = event_end.astimezone(local_tz)

        # Check if current time is within the event
        if event_start <= now <= event_end:
            return str(event_status)

    return "Free"

def wrap_text(text, font, max_width):
    lines = []
    words = text.split()
    
    while words:
        line = ''
        while words:
            test_line = line + words[0] + ' '
            # Check the width of the text
            bbox = font.getmask(test_line).getbbox()
            if bbox and bbox[2] <= max_width:
                line = test_line
                words.pop(0)
            else:
                break
        lines.append(line.strip())

    return lines

def display_status(status):
    image = Image.new('RGB', (oled.width, oled.height), 'BLACK')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    wrapped_text = wrap_text(status, font, oled.width)

    y_offset = 0
    for line in wrapped_text:    
        draw.text((0, y_offset), line, font=font, fill='WHITE')
        y_offset += font.getsize(line)[1]

    oled.ShowImage(oled.getbuffer(image))

if __name__ == '__main__':
    while True:
        file_path_or_url = read_ics_link()
        status = get_current_event_status(file_path_or_url)
        display_status(status)

        # Wait for 5 minutes before next check
        time.sleep(300)