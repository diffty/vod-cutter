import config
import json
import requests
import datetime

from interface.twitch import TwitchInterface
from log import Log


def retrieve_metadatas(vod_id, log=None):
    if log is None:
        log = Log()

    try:
        twitch_interface = TwitchInterface(
            api_client_id=config.TWITCH_API_CLIENT_ID,
            api_oauth_token=config.TWITCH_API_OAUTH_TOKEN,
            browser_client_id=config.TWITCH_BROWSER_OAUTH_TOKEN,
            browser_oauth_token=config.TWITCH_BROWSER_OAUTH_TOKEN)
    except Exception as e:
        raise e
    
    metadatas = None
    try:
        metadatas = twitch_interface.get_twitch_metadatas(vod_id)
        return metadatas
    except requests.exceptions.HTTPError as e:
        print("<!> Video not found on Twitch. Falling back on local metadatas database.")
    except Exception as e:
        print(f"<!!> Error while grabbing Twitch video metadatas : {e}")
        raise e
    
    if metadatas is None:
        vod_id_str = str(vod_id)
        with open("allmeta.json", "rb") as fp:
            metas_db = json.loads(fp.read().decode("utf-8"))
            for streamer in metas_db:
                for video_id in metas_db[streamer]:
                    if video_id == vod_id_str:
                        metadatas = metas_db[streamer][video_id]
                        metadatas["created_at"] = datetime.datetime.fromisoformat(metadatas["created_at"][:-1])
                        metadatas["published_at"] = datetime.datetime.fromisoformat(metadatas["published_at"][:-1])
                        return metadatas
            else:
                raise Exception(f"<!!> Twitch video id {vod_id} not found.")
