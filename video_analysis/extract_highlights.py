import cv2
import os
import numpy as np

def extract_keyframes(video_path, output_dir, threshold=30.0):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"FPS: {fps}, Total Frames: {total_frames}")

    ret, prev_frame = cap.read()
    if not ret:
        return

    count = 0
    saved_count = 0
    
    # Save the first frame
    cv2.imwrite(os.path.join(output_dir, f"frame_{saved_count:04d}.jpg"), prev_frame)
    saved_count += 1
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        count += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate absolute difference between current and previous frame
        diff = cv2.absdiff(gray, prev_gray)
        non_zero_count = np.count_nonzero(diff)
        percent_diff = (non_zero_count / gray.size) * 100
        
        # If significant change, save the frame
        if percent_diff > threshold:
            cv2.imwrite(os.path.join(output_dir, f"frame_{saved_count:04d}.jpg"), frame)
            saved_count += 1
            prev_gray = gray
            print(f"Saved frame {count} with diff {percent_diff:.2f}%")
            
    cap.release()
    print(f"Done. Extracted {saved_count} frames.")

if __name__ == "__main__":
    extract_keyframes("video_analysis/rec_test.mp4", "video_analysis/highlights")
