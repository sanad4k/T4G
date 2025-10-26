import RPi.GPIO as GPIO
import time
import os
import threading
import subprocess  # <-- Import subprocess
from picamera2 import Picamera2, Preview
from ultralytics import YOLO

# --- Configuration ---
SENSOR_PIN = 17       # GPIO pin for the PIR sensor
BURST_COUNT = 5     # Number of images to take on detection
MODEL_NAME = './common.pt' # Nano model. Smallest and fastest.
LOG_DIR = "detections" # Directory to save images with detections

# --- Global Objects ---
# We use a threading.Event to signal from the interrupt to the main loop
# This is thread-safe and very efficient.
detection_event = threading.Event()

# Create the log directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# --- 1. GPIO Callback Function (MUST BE FAST) ---
def motion_detected_callback(channel):
    """
    Called by RPi.GPIO when motion is detected.
    This function should be as fast as possible.
    All it does is set an 'Event' flag.
    """
    if not detection_event.is_set():
        print(f"\nMotion detected at {time.ctime()}! Triggering processor.")
        # Set the event. The processing thread is waiting for this.
        detection_event.set()

# --- 2. YOLO Processing Function (Runs in a Separate Thread) ---
def yolo_processor(picam2, yolo_model):
    """
    This function runs in its own thread. It waits for the
    'detection_event' and then runs the slow camera/YOLO process.
    """
    print("YOLO processor thread started. Waiting for motion...")
    
    while True:
        # Wait until the event is set (by the GPIO callback)
        detection_event.wait() 
        
        print("Processing thread active. Capturing burst...")
        start_time = time.time()

        # --- New variables for averaging ---
        total_confidence = 0.0
        frames_with_detections = 0
        detected_labels = []
        # --- End of new variables ---

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

        end_time = time.time()
        print(f"Burst processing finished in {end_time - start_time:.2f}s.")

        # --- New: Calculate average and call LoRa script ---
        if frames_with_detections > 0:
            average_confidence = total_confidence / frames_with_detections
            
            # Find the most common label
            if detected_labels:
                most_common_label = max(set(detected_labels), key=detected_labels.count)
            else:
                most_common_label = "unknown"

            print(f"Burst average confidence: {average_confidence:.2f}")
            print(f"Most common detection: {most_common_label}")

            # Check threshold and call lora_send.py
            if average_confidence > 0.50:
                print(f"Threshold (50%) exceeded. Calling lora_send.py...")
                try:
                    # Find the path to lora_send.py (assuming it's in the same dir)
                    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
                    LORA_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "serial.py")
                    
                    # Convert confidence to a percentage string (e.g., "75")
                    confidence_percent = f"{average_confidence * 100:.0f}"
                    python_executable = sys.executable
                    # Call the script: python3 lora_send.py "person" "75"
                    subprocess.Popen([
                        python_executable, 
                        LORA_SCRIPT_PATH, 
                        most_common_label, 
                        confidence_percent
                    ])
                    print(f"Called LoRa script with: {most_common_label}, {confidence_percent}%")

                except FileNotFoundError:
                    print(f"Error: Could not find lora_send.py")
                except Exception as e:
                    print(f"Error calling LoRa script: {e}")
            else:
                print("Average confidence below 0.50, not sending LoRa message.")
        else:
            print("No detections in this burst, no LoRa message sent.")
        # --- End of new logic ---

        # Clear the event flag so we can be triggered again
        detection_event.clear()
        print("YOLO processor is waiting for next motion event...")


# --- 3. Main Script ---
try:
    print("Initializing components...")
    
    # --- Initialize Camera ---
    picam2 = Picamera2()
    # Configure for high-res still capture
    cam_config = picam2.create_still_configuration(main={"size": (1280, 720)})
    picam2.configure(cam_config)
    picam2.start()
    print("Camera initialized and started.")
    
    # --- Initialize YOLO Model ---
    # This will download yolov8n.pt if you don't have it
    print(f"Loading YOLO model ({MODEL_NAME})... (This may take a moment)")
    model = YOLO(MODEL_NAME)
    print("YOLO model loaded.")
    
    # --- Initialize GPIO ---
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SENSOR_PIN, GPIO.IN)
    GPIO.add_event_detect(
        SENSOR_PIN, 
        GPIO.RISING, 
        callback=motion_detected_callback, 
        bouncetime=3000 # 3-second bouncetime to avoid constant triggers
    )
    print("GPIO interrupt configured.")

    # --- Start the YOLO processor thread ---
    # We pass the camera and model objects to the thread
    processor_thread = threading.Thread(
        target=yolo_processor, 
        args=(picam2, model), 
        daemon=True # A daemon thread exits when the main script exits
    )
    processor_thread.start()

    # --- Keep Main Thread Alive ---
    print("--- Smart Camera System is Active ---")
    print("Press Ctrl+C to exit.")
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping script...")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Clean up all resources
    print("Cleaning up...")
    GPIO.cleanup()
    picam2.stop()
    print("GPIO and Camera stopped. Exiting.")
