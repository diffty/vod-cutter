import requests
import json

import config


def get_video_thumbnails_manifest_url(twitch_video_id):
    r = requests.post(
        "https://gql.twitch.tv/gql",
        headers={
            'Client-Id': config.TWITCH_BROWSER_CLIENT_ID,
            f'Authentification': 'OAuth ' + config.TWITCH_BROWSER_OAUTH_TOKEN,
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


def get_thumbnails_url(manifest_url):
    r = requests.get(manifest_url)
    thumbnails_manifest = r.json()

    thumbnails_base_url = "/".join(manifest_url.split("/")[:-1])

    images = {}

    for m in thumbnails_manifest:
        for i in m["images"]:
            full_url = thumbnails_base_url + "/" + i
            images[i] = full_url
    
    return thumbnails_manifest, images


if __name__ == "__main__":
    VIDEO_ID = 1017112988

    thumbnails_manifest_url = get_video_thumbnails_manifest_url(VIDEO_ID)
    thumbnails_manifest, images = get_thumbnails_url(thumbnails_manifest_url)

    print(thumbnails_manifest, images)
