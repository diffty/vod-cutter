import os
import subprocess

import youtube_dl
import streamlink

import utils.time


def get_duration(video_url):
    ydl_opts = {
        'noplaylist': True,
        'quiet': True,
        'simulate': True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        dictMeta = ydl.extract_info(video_url, download=True)
        return dictMeta["duration"]


def download_audio(input_url, output_video, start_time=None, duration=None, rate=None):
    streams = streamlink.streams(input_url)

    audio_sources = list(filter(lambda n: "audio" in n, streams))
    
    ffmpeg_flags = ""
    streamlink_flags = ""
    
    if audio_sources:
        if rate:
            ffmpeg_flags += f" -ar {rate}"
        
        if start_time:
            if type(start_time) is float:
                d = get_duration(input_url)
                start_time = utils.time.format_time(start_time * d)
                print(start_time)

            streamlink_flags += f" --hls-start-offset {start_time}"
        
        if duration:
            streamlink_flags += f" --hls-duration {duration}"
        
        # ffmpeg -ss 00:30:00 -to 00:30:30 -i {url_video_or_playlist} caca.mp4
        print(f'streamlink {streamlink_flags} --player-passthrough hls "{input_url}" {audio_sources[0]} -O | ffmpeg -y -i pipe:0 {ffmpeg_flags} {output_video}')
        process = subprocess.Popen(f'streamlink {streamlink_flags} --player-passthrough hls "{input_url}" {audio_sources[0]} -O | ffmpeg -y -i pipe:0 {ffmpeg_flags} {output_video}', shell=True)
        process.wait()
        return process.returncode == 0



def find_offset(reference_video_url, permanent_video_url):
    #download_audio(reference_video_url, "temp_ref_audio.wav", rate=8000)
    download_audio(permanent_video_url, "temp_prm_audio.wav", start_time=0.5, duration="00:01:00", rate=8000)


if __name__ == "__main__":
    find_offset("https://www.twitch.tv/videos/996694279", "https://www.youtube.com/watch?v=S3iYAp-RYok")
