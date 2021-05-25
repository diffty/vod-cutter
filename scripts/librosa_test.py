import io
import librosa
import numpy
from urllib.request import urlopen


#librosa.load(, duration=1)

#source_fp = io.BytesIO(urlopen("file:///Users/diffty/Desktop/test.wav").read())
#source_stream = librosa.stream(source_fp, block_length=256, frame_length=4096, hop_length=1024)
source_stream, source_rate = librosa.load("/Users/diffty/Desktop/test.wav")

#template_fp = io.BytesIO(urlopen("file:///Users/diffty/Desktop/test_cropped.wav").read())
template_stream, template_rate = librosa.load("/Users/diffty/Desktop/test_cropped.wav")

print(len(template_stream))
print(template_rate)

frames = librosa.util.frame(template_stream, frame_length=template_rate, hop_length=template_rate/3, axis=-1)


for f in frames:
    print(f)
    template_stft = librosa.stft(f, center=False)


for y_block in source_stream:
    d_block = librosa.stft(y_block, center=False)
    print(d_block)

    cac = numpy.correlate(d_block, template_stft)
    print(cac)