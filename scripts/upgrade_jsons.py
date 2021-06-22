import os
import datetime
import re
import csv
import shutil
import json
import time

from medias import get_video_duration
from medias.parsers import get_video_service_id
from metadatas.retrieve import retrieve_metadatas
from metadatas.write import export_metadatas


LOG_REG = re.compile(r"(?:Starting to download a chunk of (\d{2}:\d{2}:\d{2}) of (https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)) at (\d{2}:\d{2}:\d{2})|Download duration : (\d{2}:\d{2}:\d{2})|Found sample \(maybe\) in permanent video at (\d{2}:\d{2}:\d{2})|Search duration : (\d{2}:\d{2}:\d{2})|Calculated time offset: (-?\d+(?:.\d*)?))")
FILENAME_REG = re.compile(r"([a-z_]+)_(\d+)_(\d+)_([a-z0-9-_]+)\.log", re.I)
LOGS_DIR = "C:/Users/DiFFtY/Downloads/Telegram Desktop/metadatas_01"
OK_LOGS_DIR = "C:/Users/DiFFtY/Downloads/Telegram Desktop/metadatas_01/OK_AND_UPGRADED"


if not os.path.exists(OK_LOGS_DIR):
    os.makedirs(OK_LOGS_DIR)


def parse_str_time(time_str: str):
    res = re.search(r"(\d+):(\d+):(\d+)", time_str)
    if res:
        secs = int(res.group(3))
        mins = int(res.group(2))
        hours = int(res.group(1))
        return secs + mins * 60 + hours * 3600


def json_default(o):
        if type(o) is datetime.datetime:
            return o.isoformat()
        else:
            return json.JSONEncoder.default(o)


for log_filename in os.listdir(LOGS_DIR):
    if os.path.splitext(log_filename)[1].lower() == ".log":
        parse_filename_res = FILENAME_REG.search(log_filename)
        if parse_filename_res:
            streamer_login = parse_filename_res.group(1)
            creation_timestamp = parse_filename_res.group(2)
            creation_datetime = datetime.datetime(
                year=int(creation_timestamp[0:4]),
                month=int(creation_timestamp[4:6]),
                day=int(creation_timestamp[6:8]),
                hour=int(creation_timestamp[8:10]),
                minute=int(creation_timestamp[10:12]),
                second=int(creation_timestamp[12:14]))
            src_id = parse_filename_res.group(3)
            prm_id = parse_filename_res.group(4)
        else:
            raise Exception(f"<!!> Can't properly parse log filename {log_filename}")
        
        log_filepath = f"{LOGS_DIR}/{log_filename}"
        fp_log = open(log_filepath, "r")

        parse_log_res = LOG_REG.findall(fp_log.read())
        if parse_log_res:
            chunk_duration = parse_log_res[0][0]
            perm_url = parse_log_res[0][1]
            chunk_pos_in_perm = parse_log_res[0][2]
            dl_duration = parse_log_res[1][3]
            sample_pos = parse_log_res[2][4]
            search_duration = parse_log_res[3][5]
            processed_time_offset = parse_log_res[4][6]
            
        else:
            raise Exception(f"<!!> Can't properly parse data in log {log_filename}")
        
        if float(processed_time_offset) > 10.:
            print(f"<i> {processed_time_offset=} > 10, skipping.")
            continue

        json_filename = os.path.splitext(log_filename)[0] + ".json"
        json_filepath = f"{LOGS_DIR}/{json_filename}"

        with open(json_filepath) as fp_json:
            json_data = json.load(fp_json)
            prm_video_service = json_data["permanent_id"]["service"]
        
            src_metadatas = retrieve_metadatas(src_id)

            metas = export_metadatas(src_id, prm_id, prm_video_service, get_video_duration(perm_url), float(processed_time_offset))
            
            json_ok_filepath = f"{OK_LOGS_DIR}/{json_filename}"

            print(f"<i> Writing to {json_ok_filepath}")
            with open(json_ok_filepath, "w") as fp_ok_json:
                json.dump(metas, fp_ok_json, indent=4, default=json_default)
