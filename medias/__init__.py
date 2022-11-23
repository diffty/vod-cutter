import youtube_dl
import streamlink
import subprocess
import os
import re


def get_video_duration(video_url):
    ydl_opts = {
        'noplaylist': True,
        'quiet': True,
        'simulate': True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        dict_meta = ydl.extract_info(video_url, download=True)
        return dict_meta["duration"]


def get_audio_stream_url(video_url):
    streams = streamlink.streams(video_url)

    audio_sources = list(filter(lambda n: "audio" in n, streams))

    if audio_sources:
        audio_source_name = audio_sources[0]
        return streams[audio_source_name].url


def get_media_stream_url(media_url):
    is_local = False

    if re.search(r"^(?:/|[a-z]:[\\/])", media_url, re.I):
        media_url = "file://" + media_url
        is_local = True
    else:
        media_url = media_url

    if not is_local:
        streams = streamlink.streams(media_url)
        if streams:
            return streams["best"].url
        else:
            return media_url
    else:
        return media_url


def download_audio(input_url, output_video, start_time=None, duration=None, rate=None):
    audio_stream_url = get_audio_stream_url(input_url)
    
    ffmpeg_flags = []
    
    if audio_stream_url:
        if rate:
            ffmpeg_flags += ["-ar", str(rate)]
        
        if start_time:
            ffmpeg_flags += ["-ss", str(start_time)]
        
        if duration:
            ffmpeg_flags += ["-t", str(duration)]
        
        process = subprocess.Popen(['ffmpeg', '-y', '-i', audio_stream_url, *ffmpeg_flags, output_video])
        process.wait()
        return process.returncode == 0
    
    return False


def download_audio_ytdl(input_url, output_video, start_time=None, duration=None, rate=None):
    output_video_basename = os.path.splitext(output_video)[0]

    ffmpeg_flags = []
    
    if rate:
        ffmpeg_flags += ["-ar", str(rate)]
    
    if start_time:
        ffmpeg_flags += ["-ss", str(start_time)]
    
    if duration:
        ffmpeg_flags += ["-t", str(duration)]
    
    # youtube-dl --postprocessor-args "-ss 00:01:00 -to 00:02:00" "https://www.youtube.com/watch?v=dc7I-i7sPrg"
    process = subprocess.Popen(['youtube-dl', '-x', '--audio-format', 'wav', '-f', '249', '-o', f'{output_video_basename}.%(ext)s', '--no-playlist', '--postprocessor-args', " ".join(ffmpeg_flags), input_url])
    process.wait()
    return process.returncode == 0


