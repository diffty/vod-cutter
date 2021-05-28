import os
import re
import time
import json
import datetime
import subprocess
import pprint

import youtube_dl
import streamlink
from youtube_dl.utils import date_formats

import utils.time
import detection.sound

import config

from interface.twitch import TwitchInterface


EXPORT_METADATAS_PATH = "metadatas"


#TODO: workaround pour quand streamlink veut pas dl une vidéo youtube dmca'd https://askubuntu.com/questions/1120799/how-to-play-protected-youtube-videos-in-mpv
# https://ostechnix.com/download-a-portion-of-youtube-video-with-youtube-dl-and-ffmpeg/

class Log:
    def __init__(self):
        self.log = []

    def add(self, msg, prefix="i"):
        full_msg = f"[{utils.time.format_time(time.time())}][{prefix}] {msg}"
        print(full_msg)
        self.log.append(full_msg)
    
    def write_to_disk(self, filepath):
        fp = open(filepath, "w")
        fp.write("\n".join(self.log))
        fp.close()
    

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


def get_metadata_filename(export_metadatas_folder, metadatas, ref_twitch_id, prm_video_id):
    return f"{export_metadatas_folder}/{metadatas['user_login']}_{datetime.datetime.fromisoformat(metadatas['created_at']).strftime('%Y%m%d%H%M%S')}_{ref_twitch_id}_{prm_video_id}.json"


def write_metadatas(metadatas_filename, metadatas):
    metadatas_dir = os.path.dirname(metadatas_filename)

    if not (os.path.exists(metadatas_dir) and os.path.isdir(metadatas_dir)):
        os.makedirs(metadatas_dir)
        
    def json_default(o):
        if type(o) is datetime.datetime:
            return o.isoformat()
        else:
            return json.JSONEncoder.default(o)

    fp = open(metadatas_filename, "w")
    fp.write(json.dumps(metadatas, indent=4, default=json_default))
    fp.close()


def find_offset(ref_video_url, prm_video_url_list, prm_video_pos=0.5):
    prm_video_start_time_list = []

    for prm_video_url in prm_video_url_list:
        prm_video_start_time = prm_video_pos * get_video_duration(prm_video_url)
        prm_video_start_time_list.append(prm_video_start_time)
    
    download_audio(ref_video_url, "temp_ref_audio.wav", rate=8000)

    offset_list = []

    for i, prm_video_url in enumerate(prm_video_url_list):
        log = Log()

        prm_video_start_time_str = utils.time.format_time(prm_video_start_time_list[i])

        log.add(f"Starting to download a chunk of 00:01:00 of {prm_video_url} at {prm_video_start_time_str}")

        download_start_time = time.time()

        download_audio(prm_video_url, "temp_prm_audio.wav", start_time=prm_video_start_time_str, duration="00:01:00", rate=8000)

        download_time = time.time() - download_start_time
        log.add(f"Downloaded permanent video chunk. Download duration : {utils.time.format_time(download_time)} ({round(download_time, 2)}s)")

        search_start_time = time.time()

        detected_sample_time, max_value = detection.sound.find_audio_sample("temp_ref_audio.wav", "temp_prm_audio.wav")

        search_time = time.time() - search_start_time
        log.add(f"Found sample (maybe) in permanent video at {utils.time.format_time(detected_sample_time)}. Search duration : {utils.time.format_time(search_time)} ({round(search_time, 2)}s)")

        #print(f"Sample for {prm_video_url}, starting at {prm_video_start_time_str} may be found at : {utils.time.format_time(detected_sample_time)} ({round(detected_sample_time, 2)}s)")
        offset_list.append(prm_video_start_time - detected_sample_time)

        try:
            ref_video_id, ref_video_service = get_video_service_id(ref_video_url)
        except Exception as e:
            log.add(f"Reference id parse: {e}", prefix="!!")
            raise e
        
        prm_video_id, prm_video_service = get_video_service_id(prm_video_url)

        metadatas = export_metadatas(ref_video_id, prm_video_id, prm_video_service, detected_sample_time, prm_video_start_time, log=log)
        metadatas_filename = get_metadata_filename(EXPORT_METADATAS_PATH, metadatas, ref_video_id, prm_video_id)
        write_metadatas(metadatas_filename, metadatas)

        log.write_to_disk(os.path.splitext(metadatas_filename)[0] + ".log")

    return offset_list



# TODO: parsers.py
def get_youtube_id_from_url(url):
        # Ressource pour plus tard : https://webapps.stackexchange.com/questions/54443/format-for-id-of-youtube-video
        parsed_url = re.search("v=([0-9A-Za-z_-]+)", url, re.I)

        if parsed_url:
            video_id = parsed_url.group(1)
            return video_id
        else:
            raise Exception(f"<!!> Can't find video Youtube id in video url ({url})")


def get_twitch_id_from_url(url):
    parsed_url = re.search("([0-9]+)\.mp4$", url, re.I)

    if parsed_url:
        video_id = parsed_url.group(1)
        return int(video_id)
    else:
        parsed_url = re.search("videos/([0-9]+)", url, re.I)
        if parsed_url:
            video_id = parsed_url.group(1)
            return int(video_id)
        else:
            raise Exception(f"<!!> Can't find video Twitch id in video url ({url})")
# TODO: /parsers.py


def get_video_service_id(video_url):
    if "twitch.tv" in video_url:
        video_id = get_twitch_id_from_url(video_url)
        video_service = "twitch"

    elif "youtube.com" in video_url:
        video_id = get_youtube_id_from_url(video_url)
        video_service = "youtube"
    
    else:
        raise Exception("<!!> Unknown hosting service for permanent video")
    
    return video_id, video_service


def export_metadatas(ref_video_id, prm_video_id, prm_video_service, detected_sample_time, prm_video_start_time, log):
    if log is None:
        log = Log()
    
    new_metadatas = {}
    
    try:
        twitch_interface = TwitchInterface(
            api_client_id=config.TWITCH_API_CLIENT_ID,
            api_oauth_token=config.TWITCH_API_OAUTH_TOKEN,
            browser_client_id=config.TWITCH_BROWSER_OAUTH_TOKEN,
            browser_oauth_token=config.TWITCH_BROWSER_OAUTH_TOKEN)
    except Exception as e:
        log.add(f"TwitchInterface Init: {e}", prefix="!!")
        raise e

    try:
        metadatas = twitch_interface.get_twitch_metadatas(ref_video_id)
    except Exception as e:
        log.add(f"Reference twitch video metadatas grabbing : {e}", prefix="!!")
        raise e

    new_metadatas.update(metadatas)

    new_metadatas["permanent_id"] = {
        "id": prm_video_id,
        "service": prm_video_service,
    }

    # Get ref video metadatas
    created_at = metadatas.get("created_at")

    time_offset = prm_video_start_time - detected_sample_time
    log.add(f"Calculated time offset: {time_offset}")
    corrected_time = created_at - datetime.timedelta(seconds=time_offset)

    new_metadatas["created_at"] = corrected_time.isoformat()

    return new_metadatas


if __name__ == "__main__":
    #offset_list = find_offset("https://www.twitch.tv/videos/995650292", ["https://www.youtube.com/watch?v=atdQeh6NLZQ", "https://www.youtube.com/watch?v=bXuDRvjBsxw", "https://www.youtube.com/watch?v=_0TDeDgcI5c", "https://www.youtube.com/watch?v=g3pzgTN1Dtc", "https://www.youtube.com/watch?v=NlNvh57clj0"])
    #find_offset("https://www.twitch.tv/videos/996694279",  ["https://www.youtube.com/watch?v=zJPLYLdCIJs&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=6",  "https://www.youtube.com/watch?v=14--kkylPdQ&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=7",  "https://www.youtube.com/watch?v=fBFJxE-OVs4&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=8",  "https://www.youtube.com/watch?v=gn_0PI1wl8U&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=9",  "https://www.youtube.com/watch?v=SwldmgcEI1Y&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=10"])
    #find_offset("https://www.twitch.tv/videos/999452734",  ["https://www.youtube.com/watch?v=wL_MFJ0viYU&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=11", "https://www.youtube.com/watch?v=8dTKqXkbP1M&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=13", "https://www.youtube.com/watch?v=xSBCWkoeDO0&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=13", "https://www.youtube.com/watch?v=-daAfRAEfgk&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=14"])
    #find_offset("https://www.twitch.tv/videos/1000471040", ["https://www.youtube.com/watch?v=dIiwdlNW0WA&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=15", "https://www.youtube.com/watch?v=DH82Not6b_Y&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=16", "https://www.youtube.com/watch?v=KY7OBbAIYMg&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=17"])
    #find_offset("https://www.twitch.tv/videos/1001681496", ["https://www.youtube.com/watch?v=wvOxr1bsa10&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=18", "https://www.youtube.com/watch?v=LCe_CLtPWE8&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=19", "https://www.youtube.com/watch?v=XFlirwhCdDI&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=21", "https://www.youtube.com/watch?v=qzpKIpy1j-E&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=22", "https://www.youtube.com/watch?v=WNbSUsy5xo0&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=23"])
    #find_offset("https://www.twitch.tv/videos/1001681496", ["https://www.youtube.com/watch?v=qzpKIpy1j-E&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=22", "https://www.youtube.com/watch?v=WNbSUsy5xo0&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=23"])
    #find_offset("https://www.twitch.tv/videos/1002798594", ["https://www.youtube.com/watch?v=WNbSUsy5xo0&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=23", "https://www.youtube.com/watch?v=UWT_sJMpQ6c&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=24", "https://www.youtube.com/watch?v=2ijpvTcpxkA&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=25", "https://www.youtube.com/watch?v=DCahT3LeznE&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=26", "https://www.youtube.com/watch?v=DCahT3LeznE&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=26",  "https://www.youtube.com/watch?v=GMH0mCkwTLA&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=27"])
    #find_offset("https://www.twitch.tv/videos/1003959589", ["https://www.youtube.com/watch?v=CkwJjYeHDzI&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=28", "https://www.youtube.com/watch?v=oYypbGWNIUQ&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=29", "https://www.youtube.com/watch?v=cAfFbpK2lgA&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=30"])

    #PROBLEME: find_offset("https://www.twitch.tv/videos/1001681496", ["https://www.youtube.com/watch?v=XFlirwhCdDI&list=PLNdO3e3fKSGe0HPd1jcp_n999VeWEJQHA&index=21"])

    # AVA & aypierre ; à checker
    #find_offset("https://www.twitch.tv/videos/996937193", ["https://www.twitch.tv/videos/1000271551"])
    #find_offset("https://www.twitch.tv/videos/998153385", ["https://www.twitch.tv/videos/1000273310"])
    #find_offset("https://www.twitch.tv/videos/1000679575", ["https://www.twitch.tv/videos/1001332596"])
    #find_offset("https://www.twitch.tv/videos/1001379818", ["https://www.twitch.tv/videos/1002440059"])
    #find_offset("https://www.twitch.tv/videos/1001766035", ["https://www.twitch.tv/videos/1003565272"])
    #find_offset("https://www.twitch.tv/videos/1002908573", ["https://www.twitch.tv/videos/1005858235"])
    #find_offset("https://www.twitch.tv/videos/1005146011", ["https://www.twitch.tv/videos/1008367627"])
    #find_offset("https://www.twitch.tv/videos/1007552832", ["https://www.twitch.tv/videos/1009447383"])
    #find_offset("https://www.twitch.tv/videos/1008811749", ["https://www.twitch.tv/videos/1010708066"])
    #find_offset("https://www.twitch.tv/videos/1009795534", ["https://www.twitch.tv/videos/1011732227"])
    #find_offset("https://www.twitch.tv/videos/995671122", ["https://www.youtube.com/watch?v=CKu2VE2NofQ"])
    #find_offset("https://www.twitch.tv/videos/996963096", ["https://www.youtube.com/watch?v=h-jdu5AFIes"])
    #find_offset("https://www.twitch.tv/videos/1001769976", ["https://www.youtube.com/watch?v=2SDe1zvhQU0"])
    #find_offset("https://www.twitch.tv/videos/1002604196", ["https://www.youtube.com/watch?v=-V_3WaAdjag"])
    #find_offset("https://www.twitch.tv/videos/1004020761", ["https://www.youtube.com/watch?v=BiuYanbs8sc"])
    #find_offset("https://www.twitch.tv/videos/1004878743", ["https://www.youtube.com/watch?v=m9CVPvY_tZs"])

    find_offset("https://www.twitch.tv/videos/995712212", ["https://www.youtube.com/watch?v=WrtjHHKee_Q&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-", "https://www.youtube.com/watch?v=SWkkjDeaUY0&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=2", "https://www.youtube.com/watch?v=pqJroXlQ7zQ&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=3"])
    find_offset("https://www.twitch.tv/videos/996918701", ["https://www.youtube.com/watch?v=V6W35xiyHY8&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=4", "https://www.youtube.com/watch?v=epTzz4kePlg&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=5", "https://www.youtube.com/watch?v=knOQREWoZvs&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=6"])
    find_offset("https://www.twitch.tv/videos/999197520", ["https://www.youtube.com/watch?v=RhqOZ2XEbeM&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=7", "https://www.youtube.com/watch?v=1tdUGkgpEuc&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=8", "https://www.youtube.com/watch?v=HpCB2D5Lda0&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=9"])
    find_offset("https://www.twitch.tv/videos/1000562372", ["https://www.youtube.com/watch?v=7HVE9VR_YjE&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=13", "https://www.youtube.com/watch?v=uryH4x1UFGY&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=14", "https://www.youtube.com/watch?v=wapMVEivwkM&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=15"])
    find_offset("https://www.twitch.tv/videos/1002655305", ["https://www.youtube.com/watch?v=hiE1U91VFqE&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=16", "https://www.youtube.com/watch?v=s79BtjKJptk&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=17", "https://www.youtube.com/watch?v=u1EjGTwPA0w&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=18"])
    find_offset("https://www.twitch.tv/videos/1003925521", ["https://www.youtube.com/watch?v=0uQ6qYTdHcc&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=19", "https://www.youtube.com/watch?v=ucD8oGRd6k4&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=20", "https://www.youtube.com/watch?v=puNtuu_-RX8&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=21"])
    find_offset("https://www.twitch.tv/videos/1005121881", ["https://www.youtube.com/watch?v=nHrFKYFyW0I&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=22", "https://www.youtube.com/watch?v=cUUrdUI578M&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=23", "https://www.youtube.com/watch?v=XKjJQcK-Xgg&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=24"])
    find_offset("https://www.twitch.tv/videos/1007510097", ["https://www.youtube.com/watch?v=5K8vCWdHmZ4&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=25", "https://www.youtube.com/watch?v=aQVlXINGbY8&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=26"])
    find_offset("https://www.twitch.tv/videos/1008764624", ["https://www.youtube.com/watch?v=UGirZ8up7yg&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=27", "https://www.youtube.com/watch?v=wnOfDtaJsKc&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=28", "https://www.youtube.com/watch?v=1NNWH9e_lcU&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=29"])
    find_offset("https://www.twitch.tv/videos/1009842294", ["https://www.youtube.com/watch?v=m_ih9Zprt6Q&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=30", "https://www.youtube.com/watch?v=GNaKBtu6p4w&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=31"])
    find_offset("https://www.twitch.tv/videos/1010853999", ["https://www.youtube.com/watch?v=KfAKNqGk6mc&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=32", "https://www.youtube.com/watch?v=q-hRuNmyw7E&list=PLlY7oa15ZT9nahQfIZ9Le0O_fW7Foz3m-&index=33"])