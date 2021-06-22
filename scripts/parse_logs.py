import os
import datetime
import re
import csv
import shutil
import json


LOG_REG = re.compile(r"(?:Starting to download a chunk of (\d{2}:\d{2}:\d{2}) of (https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)) at (\d{2}:\d{2}:\d{2})|Download duration : (\d{2}:\d{2}:\d{2})|Found sample \(maybe\) in permanent video at (\d{2}:\d{2}:\d{2})|Search duration : (\d{2}:\d{2}:\d{2})|Calculated time offset: (-?\d+(?:.\d*)?))")
FILENAME_REG = re.compile(r"([a-z0-9_]+)_(\d+)_(\d+)_([a-z0-9-_]+)\.log", re.I)
LOGS_DIR = "C:/Users/DiFFtY/Downloads/Telegram Desktop/vod_cutter (2)/metadatas_01/OK_AND_UPGRADED"
OK_LOGS_DIR = "metadatas/OK"


def parse_str_time(time_str: str):
    res = re.search(r"(\d+):(\d+):(\d+)", time_str)
    if res:
        secs = int(res.group(3))
        mins = int(res.group(2))
        hours = int(res.group(1))
        return secs + mins * 60 + hours * 3600

sync_tool_playlist = []

with open("results.csv", "w", newline='') as csvfile:
    csvwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writerow([
        "streamer_login",
        "creation_timestamp",
        "src_id",
        "prm_id",
        "time_offset",
        "src_url",
        "prm_url",
        "sample_pos",
        "found_pos",
        "dl_duration",
        "search_duration",
    ])

    for log_filename in os.listdir(LOGS_DIR):
        if os.path.splitext(log_filename)[1].lower() == ".log":
            json_filepath = LOGS_DIR + "/" + os.path.splitext(log_filename)[0] + ".json"

            if not os.path.exists(json_filepath):
                continue

            with open(json_filepath, "r") as fp:
                data = json.load(fp)
                time_offset = data["permanent_id"]["created_delay"] / 1000.

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

            src_url = f"https://www.twitch.tv/videos/{src_id}"

            csvwriter.writerow([
                streamer_login,
                creation_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                src_id,
                prm_id,
                round(float(time_offset), 3),
                src_url,
                perm_url,
                sample_pos,
                chunk_pos_in_perm,
                dl_duration,
                search_duration,
            ])

            #shutil.copyfile(f"{LOGS_DIR}/{log_filename}", f"{OK_LOGS_DIR}/{log_filename}")
            #print("{} -> {}".format(f"{LOGS_DIR}/{log_filename}", f"{OK_LOGS_DIR}/{log_filename}"))
            sync_tool_playlist.append([
                {
                    "url": src_url,
                    "time": parse_str_time(sample_pos),
                },
                {
                    "url": perm_url,
                    "time": parse_str_time(chunk_pos_in_perm),
                }
            ])

    with open("synced_playlist.json", "w") as fp:
        json.dump(sync_tool_playlist, fp, indent=4)
