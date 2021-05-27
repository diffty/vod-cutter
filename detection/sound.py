import os
import math
import time

import numpy as np
import librosa


# Implementation based on https://stackoverflow.com/questions/52572693/find-sound-effect-inside-an-audio-file
# See also https://librosa.org/blog/2019/07/29/stream-processing/

# D:\Freddy\Twitch\RPZ>ffmpeg -i "D:\Freddy\Twitch\RPZ\AntoineDanielLive_20210424_203943_DONATIEN DE MONTAZAC IS BACK IN TOWN (Nouvelle Emote DONATIEN) !rpz !vod_999452734.mp4" -ss 01:50:00 -to 01:51:00 D:\bigass_test_cut.wav
# Found sample at 01:50:00.00 in 2042.44s


def format_time(t):
    formatted_time  = f"{str(math.floor(t / 3600)).zfill(2)}:"
    formatted_time += f"{str(math.floor(t / 60 % 60)).zfill(2)}:"
    formatted_time += f"{str(math.floor(t) % 60).zfill(2)}."
    formatted_time += f"{str(math.floor((t - math.floor(t)) * 100)).zfill(2)}"

    return formatted_time


def find_audio_sample(source_path, template_path):
    template_sound, template_rate = librosa.load(template_path, sr=None)

    source_rate = librosa.get_samplerate(source_path)

    frame_length = len(template_sound)
    block_length = 1024
    hop_length = 128      # 512

    source_stream = librosa.stream(source_path,
                                   block_length=block_length,
                                   frame_length=frame_length,
                                   hop_length=int(hop_length))

    max_value = 0
    max_time = -1

    for i_block, block in enumerate(source_stream):
        i_frame = 0

        while i_frame * hop_length < hop_length * (block_length - 1):
            frame = block[i_frame * hop_length : i_frame * hop_length + frame_length]

            if frame.shape[0] < frame_length:
                break

            curr_time = (i_block * block_length * hop_length + i_frame * hop_length) / source_rate

            #print(f"Processing {format_time(curr_time)}")

            corr = abs(np.correlate(frame, template_sound)[0])

            if max_value < corr:
                max_time = curr_time
                max_value = corr

            i_frame += 1

    return max_time, max_value


if __name__ == "__main__":
    t_start = time.time()

    found_time, found_value = find_audio_sample("C:/Users/f.clement/Desktop/vod_cutter/temp_ref_audio.wav",
                                                "C:/Users/f.clement/Desktop/vod_cutter/temp_prm_audio.wav")

    t_end = time.time()

    print(f"Found sample at {format_time(found_time)} in {round(t_end - t_start, 2)}s")
