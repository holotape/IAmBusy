import datetime
import os
import sys
import time
import pytz
import requests
from icalendar import Calendar
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO
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
            summary = str(event.get('summary'))
            if "Focus" in summary:
                return "Do Not Disturb  - ", "red", "dnd-128.png"
            elif "Lunch" in summary:
                return "Out to Lunch  -", "yellow", "time-4-128.png"
            elif "WFH" in summary:
                return "Working Elsewhere  -", "blue", "house-128.png"
            else:
                return "Do Not Disturb  -", "red", "dnd-128.png"  # Default for any other event

    return "", None, None  # No event - blank screen


def display_status(status, color):
    if status:  # Only display if there is a status
        image = Image.new('RGB', (oled.width, oled.height), 'BLACK')
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
        text_color = color_map.get(color, 'WHITE')  # Get the colour or default to white
        draw.text((0, 0), status, font=font, fill=text_color)
        oled.ShowImage(oled.getbuffer(image))
    else:
        oled.clear()  # Clear the screen if there's no status

color_map = {
    "red": (255, 10, 10),
    "yellow": (255, 255, 0),
    "blue": (10, 10, 255),
}

def display_scrolling_status(status, color, icon_filename, scroll_delay=0.001):
    if not status:
        oled.clear()
        return

    icon_path = os.path.join(picdir, 'icons', icon_filename) if icon_filename else None
    icon = Image.open(icon_path) if icon_path else None

    font = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
    
    bbox = font.getbbox(status)
    text_width, text_height = bbox[2], bbox[3]
    image_width, image_height = oled.width, oled.height

    start_offset = 300
    text_x = image_width - start_offset  # Start text on the right side of the screen
    text_y = image_height - text_height  # Position text at the bottom of the screen

    bbox_restart = font.getbbox("-")
    restart_x = image_width - bbox_restart[2]  # when to restart

    while True:
        image = Image.new('RGB', (image_width, image_height), 'BLACK')
        draw = ImageDraw.Draw(image)

        if icon:
            image.paste(icon, (16, 0)) # image display coordinates

        text_color = color_map.get(color, 'WHITE')
        draw.text((text_x, text_y), status, font=font, fill=text_color)
        oled.ShowImage(oled.getbuffer(image))

        # Check if it's time to restart the message
        if text_x + text_width < restart_x:
            text_x = image_width
        else:
            text_x -= 10  # Move the text to the left

        time.sleep(scroll_delay)


if __name__ == '__main__':
    while True:
        print("Checking for new meetings...")
        file_path_or_url = read_ics_link()
        status, color, icon_filename = get_current_event_status(file_path_or_url)
        long_status = (status + "  ") * 10
        display_scrolling_status(long_status, color, icon_filename, scroll_delay=0.001)
        time.sleep(120)  # Wait 2 minutes before next check

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

def display_status(status, color=None):
    if status:
        image = Image.new('RGB', (oled.width, oled.height), 'BLACK')
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)

        # Determine text colour
        text_color = color_map.get(color, 'WHITE')

        # Wrap text
        wrapped_text = wrap_text(status, font, oled.width)
        y_offset = 0
        for line in wrapped_text:
            draw.text((0, y_offset), line, font=font, fill=text_color)
            y_offset += font.getsize(line)[1]

        oled.ShowImage(oled.getbuffer(image))
    else:
        oled.clear()  # Clear the screen if there's no status


# if __name__ == '__main__':
#      while True:
#          print("Checking for new meetings2...")
#          file_path_or_url = read_ics_link()
#          status, color, icon_filename = get_current_event_status(file_path_or_url)
#          display_status(status, color)
#          time.sleep(300)  # Wait 5 minutes before next check
