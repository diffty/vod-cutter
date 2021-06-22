import os
import datetime
import json
import math

from log import Log
from metadatas.retrieve import retrieve_metadatas
from medias import get_video_duration


def export_metadatas(ref_video_id, prm_video_id, prm_video_service, prm_video_duration, time_offset, log=None):
    if log is None:
        log = Log()
    
    new_metadatas = {}
        
    metadatas = retrieve_metadatas(ref_video_id)

    new_metadatas.update(metadatas)

    # Get ref video metadatas
    created_at = metadatas.get("created_at")

    log.add(f"Calculated time offset: {time_offset}")
    corrected_time = created_at - datetime.timedelta(seconds=time_offset)

    new_metadatas["permanent_id"] = {
        "id": prm_video_id,
        "service": prm_video_service,
        "new_created_at": corrected_time.isoformat(),
        "created_delay": math.floor(-time_offset * 1000),
        "duration": math.floor(prm_video_duration * 1000),
    }

    return new_metadatas
    

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
