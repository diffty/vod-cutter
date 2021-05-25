import math
import librosa
import numpy as np

source_stream, source_rate = librosa.load("/Users/diffty/Desktop/test.wav")
template_stream, template_rate = librosa.load("/Users/diffty/Desktop/test_cropped.wav")

frame_length = source_rate     # source_rate
hop_length = source_rate/2         # source_rate/4

S_frames = librosa.util.frame(source_stream, frame_length=frame_length, hop_length=int(hop_length), axis=0)
T_frames = librosa.util.frame(template_stream, frame_length=frame_length, hop_length=int(hop_length), axis=0)

fp = open("test.txt", "w")

for i_s, f_s in enumerate(S_frames):
    curr_time = (i_s * hop_length) / source_rate
    #print(curr_time)
    sum = 0
    for i_t, f_t in enumerate(T_frames):
        corr = np.correlate(f_s, f_t)
        sum += corr
    
    if sum > 0:
        txt = f"{str(math.floor(curr_time / 360)).zfill(2)}:{str(math.floor(curr_time / 60)).zfill(2)}:{str(math.floor(curr_time) % 60).zfill(2)}.{str(math.floor((curr_time - math.floor(curr_time)) * 60)).zfill(2)} -> {sum}"
        fp.write(txt+"\n")

fp.close()