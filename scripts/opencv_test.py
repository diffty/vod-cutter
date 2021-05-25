import cv2

vc = cv2.VideoCapture("https://dgeft87wbj63p.cloudfront.net/f1006ad7703445d63917_alexclick_41836944844_1619027230/chunked/index-dvr.m3u8")

success, image = vc.read()

success = True
count = 0

template = cv2.imread("/Users/diffty/Pictures/vlcsnap-2021-05-24-23h24m45s805.png")
template = cv2.imread("/Users/diffty/Pictures/vlcsnap-2021-05-24-23h31m16s498.png")

while success:
    success, image = vc.read()
    #cv2.imwrite("test.jpg", image)
    count += 1
    #print(count)

    res = cv2.matchTemplate(
        image, template, cv2.TM_CCOEFF_NORMED
    )

    print(res)