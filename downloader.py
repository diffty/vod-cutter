import os
import subprocess

import youtube_dl
import streamlink

import utils.time
import detection.sound


def get_video_duration(video_url):
    ydl_opts = {
        'noplaylist': True,
        'quiet': True,
        'simulate': True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        dictMeta = ydl.extract_info(video_url, download=True)
        return dictMeta["duration"]


def get_audio_stream_url(video_url):
    streams = streamlink.streams(video_url)
    audio_sources = list(filter(lambda n: "audio" in n, streams))

    if audio_sources:
        audio_source_name = audio_sources[0]
        return streams[audio_source_name].url


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


def find_offset(reference_video_url, permanent_video_url_list, permanent_video_pos=0.5):
    permanent_video_start_time_list = []

    for permanent_video_url in permanent_video_url_list:
        permanent_video_start_time = permanent_video_pos * get_video_duration(permanent_video_url)
        permanent_video_start_time_list.append(permanent_video_start_time)
    
    if not os.path.exists("temp_ref_audio.wav"):
        download_audio(reference_video_url, "temp_ref_audio.wav", rate=8000)

    offset_list = []

    for i, permanent_video_url in enumerate(permanent_video_url_list):
        permanent_video_start_time_str = utils.time.format_time(permanent_video_start_time_list[i])
        download_audio(permanent_video_url, "temp_prm_audio.wav", start_time=permanent_video_start_time_str, duration="00:01:00", rate=8000)
        detected_sample_time, max_value = detection.sound.find_audio_sample("temp_ref_audio.wav", "temp_prm_audio.wav")
        print(f"Sample for {permanent_video_url}, starting at {permanent_video_start_time_str} may be found at : {utils.time.format_time(detected_sample_time)} ({round(detected_sample_time, 2)}s)")
        offset_list.append(permanent_video_start_time - detected_sample_time)

    return offset_list


if __name__ == "__main__":
    offset_list = find_offset("https://www.twitch.tv/videos/995650292", ["https://www.youtube.com/watch?v=atdQeh6NLZQ", "https://www.youtube.com/watch?v=bXuDRvjBsxw", "https://www.youtube.com/watch?v=_0TDeDgcI5c", "https://www.youtube.com/watch?v=g3pzgTN1Dtc", "https://www.youtube.com/watch?v=NlNvh57clj0"])
    print(offset_list)
