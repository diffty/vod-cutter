import os
import re
import datetime
import shutil

from twitch import TwitchHelix

client = TwitchHelix(client_id="p1p9ua9y6bk4hly68i5yvdjzhn5yi9", oauth_token="pg24a2a6kw1iaqgq1ad4qz7uk1lrjz")

#os.chdir("D:/Freddy/Twitch/RPZ")

cwd = os.getcwd()
for f in os.listdir():
    parsed_filename = re.search("([0-9]+)\.mp4", f, re.I)

    if parsed_filename:
        video_id = parsed_filename.group(1)
        twitch_videos = client.get_videos(video_ids=[int(video_id)])

        if twitch_videos:
            twitch_video_infos = twitch_videos[0]

            user_login = twitch_video_infos['user_login']
            video_timestamp = int(datetime.datetime.timestamp(twitch_video_infos['created_at']))

            old_name = f
            new_name = f"{user_login}__{video_timestamp}__{video_id}.mp4"
            
            if old_name != new_name:
                print(f"<i> Renaming {old_name} -> {new_name}")
                shutil.move(old_name, new_name)
            else:
                print("<!> Already renamed, skipping.")