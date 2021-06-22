import re


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

