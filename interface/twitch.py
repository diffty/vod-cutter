import json
import requests

from twitch import TwitchHelix


class TwitchInterface:
    def __init__(self, api_client_id, api_oauth_token, browser_client_id, browser_oauth_token):
        self.api_client_id = api_client_id
        self.api_oauth_token = api_oauth_token
        self.browser_client_id = browser_client_id
        self.browser_oauth_token = browser_oauth_token

        self.twitch_client = TwitchHelix(
            client_id=self.api_client_id,
            oauth_token=self.api_oauth_token
        )

    def get_twitch_metadatas(self, twitch_video_id):
        twitch_videos = self.twitch_client.get_videos(video_ids=[twitch_video_id])

        if twitch_videos:
            twitch_video_infos = twitch_videos[0]
            return twitch_video_infos
        else:
            raise Exception(f"<!!> Can't find Twitch metadatas for video id {twitch_video_id}")
    
    def get_video_games_list(self, twitch_video_id):
        r = requests.post(
            "https://gql.twitch.tv/gql",
            headers={
                'Client-Id': self.browser_client_id,
                f'Authentification': 'OAuth ' + self.browser_oauth_token,
            },
            data=json.dumps([{
                "operationName": "VideoPlayer_ChapterSelectButtonVideo",
                "variables": {
                    "includePrivate": False,
                    "videoID": str(twitch_video_id)
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "8d2793384aac3773beab5e59bd5d6f585aedb923d292800119e03d40cd0f9b41"
                    }
                }
            }])
        )

        if r.status_code == 200:
            answer_data = r.json()
            moments_data = answer_data[0]["data"]["video"]["moments"]["edges"]

            moments = []

            for m in moments_data:
                moments.append(m["node"])

            return moments
        else:
            return None

    def get_video_thumbnails_manifest_url(self, twitch_video_id):
        r = requests.post(
            "https://gql.twitch.tv/gql",
            headers={
                'Client-Id': self.browser_client_id,
                f'Authentification': 'OAuth ' + self.browser_oauth_token,
            },
            data=json.dumps([{
                "operationName": "VideoPlayer_VODSeekbarPreviewVideo",
                "variables": {
                    "includePrivate": False,
                    "videoID": str(twitch_video_id)
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "07e99e4d56c5a7c67117a154777b0baf85a5ffefa393b213f4bc712ccaf85dd6"
                    }
                }
            }])
        )

        if r.status_code == 200:
            answer_data = r.json()
            
            seek_previews_url = answer_data[0]["data"]["video"]["seekPreviewsURL"]

            return seek_previews_url
        else:
            return None

    def get_thumbnails_url_from_manifest(manifest_url):
        r = requests.get(manifest_url)
        thumbnails_manifest = r.json()

        thumbnails_base_url = "/".join(manifest_url.split("/")[:-1])

        images = {}

        for m in thumbnails_manifest:
            for i in m["images"]:
                full_url = thumbnails_base_url + "/" + i
                images[i] = full_url
        
        return thumbnails_manifest, images


    
