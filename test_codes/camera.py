from picamera2 import Picamera2, Preview
from ultralytics import YOLO

BURST_COUNT =  50 
for i in range(BURST_COUNT):
            frame_start_time = time.time()
            
            # Capture an image to a NumPy array in RAM (fast)
            # We use 'main' stream for high-res capture
            image_array = picam2.capture_array("main")
            
            # Run YOLO prediction on the image
            # 'verbose=False' stops it from printing results to console
            results = yolo_model(image_array, verbose=False)
            
            # --- Process Results ---
            # 'results[0]' is the result for the first (and only) image
            result = results[0]
            
    if len(result.boxes) > 0:
                print(f"  [Frame {i+1}/{BURST_COUNT}] DETECTED {len(result.boxes)} objects.")
                
                # --- Find top detection and update average ---
                frames_with_detections += 1
                top_confidence_in_frame = 0.0
                top_label_in_frame = ""

                for box in result.boxes:
                    confidence = float(box.conf)
                    if confidence > top_confidence_in_frame:
                        top_confidence_in_frame = confidence
                        top_label_in_frame = yolo_model.names[int(box.cls)]
                
                if top_label_in_frame: # If we found a top label
                    total_confidence += top_confidence_in_frame
                    detected_labels.append(top_label_in_frame)
                # --- End of update logic ---

                # Get a timestamp for the filename
                ts = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
                filename = f"{LOG_DIR}/detection_{ts}_frame_{i+1}.jpg"
                
                # Save the annotated image (with boxes)
                result.save(filename=filename)
                print(f"    Saved detection to: {filename}")
                
                # Log what was found
                for box in result.boxes:
                    class_id = int(box.cls)
                    label = yolo_model.names[class_id]
                    confidence = float(box.conf)
                    print(f"    -> {label} (Confidence: {confidence:.2f})")
            else:
                 print(f"  [Frame {i+1}/{BURST_COUNT}] No objects detected.")

            frame_end_time = time.time()
            print(f"  Frame {i+1} took {frame_end_time - frame_start_time:.2f}s")
            
            # Try to keep a 5 FPS pace (0.2s per frame)
            # If processing was faster than 0.2s, wait.
            # If processing was slower, this does nothing.
            time.sleep(max(0, 0.2 - (frame_end_time - frame_start_time)))
