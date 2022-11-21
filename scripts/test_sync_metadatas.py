from interface import twitch
from medias import parsers

import config
import json
import re
import datetime


vod_list = [
    "https://www.twitch.tv/videos/1655443709",
    "https://www.twitch.tv/videos/1655460282",
    "https://www.twitch.tv/videos/1655280245",
]

twitch_ifc = twitch.TwitchInterface(
    api_client_id=config.TWITCH_API_CLIENT_ID,
    api_oauth_token=config.TWITCH_API_OAUTH_TOKEN,
    browser_client_id=config.TWITCH_BROWSER_OAUTH_TOKEN,
    browser_oauth_token=config.TWITCH_BROWSER_OAUTH_TOKEN
)


def convert_duration_to_seconds(duration_str):
    reg_res = re.search("(?:(\d+)h)?(?:(\d+)m)?(\d+)s", duration_str)
    if reg_res:
        hours, minutes, seconds = reg_res.groups()
        return int(seconds) + (int(minutes) if minutes else 0) * 60 + (int(hours) if hours else 0) * 3600
    else:
        return None


import streamlink

def get_media_stream_url(file_url, is_local=False):
    if not is_local:
        streams = streamlink.streams(file_url)
        if streams:
            media_url = streams["best"].url
        else:
            media_url = file_url
    else:
        media_url = file_url
    
    return media_url


import subprocess
from utils.time import format_time, parse_duration

def download_media(media_url, output_file_name, start_time, end_time, is_local=False):
    if is_local:
        cmd = [
            'ffmpeg',
            '-i', media_url,
            '-ss', start_time,
            '-to', end_time,
            '-c:v', 'copy',
            '-c:a', 'copy',
            f'{output_file_name}.mp4']
    else:
        cmd = [
            'streamlink',
            '-f',
            '--hls-start-offset', f'{format_time(start_time)}',
            '--hls-duration', f'{format_time(end_time - start_time)}',
            '--player-passthrough', 'hls',
            media_url,
            'best',
            '-o', f'{output_file_name}.mp4']
     
    process = subprocess.Popen(cmd)
    process.wait()


vod_id = parsers.get_twitch_id_from_url(vod_list[0])
metadatas = twitch_ifc.get_twitch_metadatas(vod_id)
ref_date: datetime.datetime = metadatas["created_at"]
cut_time: datetime.datetime = datetime.timedelta(hours=1, minutes=30, seconds=9)
cut_duration = datetime.timedelta(seconds=40)


for vod_url in vod_list:
    vod_id = parsers.get_twitch_id_from_url(vod_url)
    metadatas = twitch_ifc.get_twitch_metadatas(vod_id)
    start_date: datetime.datetime = metadatas["created_at"]
    diff_seconds = ref_date.timestamp() - start_date.timestamp()
    duration_secs = convert_duration_to_seconds(metadatas["duration"])

    stream_url = get_media_stream_url(vod_url)

    download_media(
        stream_url,
        metadatas["user_login"],
        cut_time.seconds + diff_seconds,
        (cut_time + cut_duration).seconds + diff_seconds)
