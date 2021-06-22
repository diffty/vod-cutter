import datetime


def get_metadata_filename(export_metadatas_folder, metadatas, ref_twitch_id, prm_video_id):
    return f"{export_metadatas_folder}/{metadatas['user_login']}_{metadatas['created_at'].strftime('%Y%m%d%H%M%S')}_{ref_twitch_id}_{prm_video_id}.json"
