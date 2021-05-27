import os
import math
import librosa

import numpy as np
import matplotlib.pyplot as plt


ref_sound_filepath = "C:/Users/f.clement/Desktop/vod_cutter/temp_ref_audio.wav"
prm_sound_filepath = "C:/Users/f.clement/Desktop/vod_cutter/temp_prm_audio.wav"

# Implementation based on https://stackoverflow.com/questions/52572693/find-sound-effect-inside-an-audio-file
# See also https://librosa.org/blog/2019/07/29/stream-processing/

source_sound, source_rate = librosa.load(ref_sound_filepath, sr=None)
template_sound, template_rate = librosa.load(prm_sound_filepath, sr=None)

source_rate = librosa.get_samplerate(ref_sound_filepath)

frame_length = len(template_sound)
hop_length = 128
block_length = 1024

source_stream = librosa.stream(ref_sound_filepath,
                               block_length=block_length,
                               frame_length=frame_length,
                               hop_length=int(hop_length))

xs = []
ys = []
abs_ys = []

for i_block, block in enumerate(source_stream):
    i_frame = 0

    while i_frame * hop_length < hop_length * (block_length - 1):
        frame = block[i_frame * hop_length : i_frame * hop_length + frame_length]

        if frame.shape[0] < frame_length:
            break

        curr_time = (i_block * block_length * hop_length + i_frame * hop_length) / source_rate

        curr_timestamp_str  = f"{str(math.floor(curr_time / 3600)).zfill(2)}:"
        curr_timestamp_str += f"{str(math.floor(curr_time / 60 % 60)).zfill(2)}:"
        curr_timestamp_str += f"{str(math.floor(curr_time) % 60).zfill(2)}."
        curr_timestamp_str += f"{str(math.floor((curr_time - math.floor(curr_time)) * 100)).zfill(2)}"

        print(f"Processing {curr_timestamp_str}")

        corr = np.correlate(frame, template_sound)[0]

        xs.append(curr_time)
        ys.append(corr)
        abs_ys.append(abs(corr))

        i_frame += 1


plt.plot(xs, ys)
plt.show()

max_idx = np.argmax(abs_ys)
max_t = xs[max_idx]

print(max_t)