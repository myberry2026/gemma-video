import cv2
import os

video_path = 'video_analysis/real_video.mp4'
cap = cv2.VideoCapture(video_path)
count = 0
saved = 0
while saved < 16:
    ret, frame = cap.read()
    if not ret: break
    if count % 10 == 0:
        cv2.imwrite(f'real_{saved:02d}.jpg', frame)
        saved += 1
    count += 1
cap.release()
print(f"Extracted {saved} frames.")
