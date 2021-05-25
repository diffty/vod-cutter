import os
import math
import librosa

import numpy as np
import matplotlib.pyplot as plt


# Implementation based on https://stackoverflow.com/questions/52572693/find-sound-effect-inside-an-audio-file

source_stream, source_rate = librosa.load(os.path.dirname(__file__) + "/" + "test.wav")
template_stream, template_rate = librosa.load(os.path.dirname(__file__) + "/" + "test_cropped3.wav")

frame_length = len(template_stream)
hop_length = 512

source_frames = librosa.util.frame(source_stream,
                              frame_length=frame_length,
                              hop_length=int(hop_length),
                              axis=0)


xs = []
ys = []
abs_ys = []

for i_s, f_s in enumerate(source_frames):
    curr_time = (i_s * hop_length) / source_rate
    
    curr_timestamp_str  = f"{str(math.floor(curr_time / 360)).zfill(2)}:"
    curr_timestamp_str += f"{str(math.floor(curr_time / 60 )).zfill(2)}:"
    curr_timestamp_str += f"{str(math.floor(curr_time) % 60).zfill(2)}."
    curr_timestamp_str += f"{str(math.floor((curr_time - math.floor(curr_time)) * 100)).zfill(2)}"

    print(f"Processing {curr_timestamp_str}")

    corr = np.correlate(f_s, template_stream)[0]

    xs.append(curr_time)
    ys.append(corr)
    abs_ys.append(abs(corr))
    

plt.plot(xs, ys)
plt.show()

max_idx = np.argmax(abs_ys)
max_t = xs[max_idx]
