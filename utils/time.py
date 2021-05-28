import re
import math
import datetime


def format_time(seconds):
    return f"{str(math.floor(seconds / 3600) % 24).zfill(2)}:{str(math.floor(seconds / 60 % 60)).zfill(2)}:{str(math.floor(seconds % 60)).zfill(2)}"


def parse_duration(d):
    print(d)
    duration_regex = re.search("(?:([0-9]+)h)?(?:([0-9]+)m)?([0-9]+)s", d, re.I)
    if duration_regex:
        hours = duration_regex.group(1)
        mins = duration_regex.group(2)
        secs = duration_regex.group(3)
        return datetime.timedelta(
            seconds=(int(secs) if secs else 0),
            minutes=(int(mins) if mins else 0),
            hours=(int(hours) if hours else 0))
    else:
        return None


if __name__ == "__main__":
    print(format_time(22870))