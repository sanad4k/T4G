import serial
import time
import glob
import sys

#AT+DTRX=1,2,5,0123456789

def find_serial_port():
    """
    Finds the first available /dev/ttyUSB* or /dev/ttyACM* port.
    Returns the port name as a string, or None if not found.
    """
    # glob.glob returns a list of matching file paths
    ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    
    if ports:
        print(f"[LoRa Script] Found serial port: {ports[0]}")
        return ports[0]
    else:
        print("[LoRa Script] Error: No /dev/ttyUSB* or /dev/ttyACM* port found.")
        return None

def send_lora_command(command_string):
    """
    Finds a serial port and sends a given command string to it.
    
    Args:
        command_string (str): The text you want to send. A newline is added.
    """
    port_name = find_serial_port()
    if not port_name:
        return # Exit if no port was found

    ser = None # Initialize ser to None
    try:
        # --- Configure Serial Port ---
        # 9600 is the baud rate. This MUST match your LoRa device's setting.
        # Common values are 9600, 19200, 57600, 115200.
        ser = serial.Serial(port_name, 9600, timeout=1)
        
        # Wait a brief moment for the connection to establish
        time.sleep(2) 

        # --- THIS IS THE DATA THAT IS SENT ---
        # We add a newline character (\n) because most serial
        # devices listen for a newline to know the command is complete.
        data_to_send = f"{command_string}\n"
        
        # --- Sending the Data ---
        # We must .encode() the string into raw bytes.
        ser.write(data_to_send.encode('utf-8'))
        
        print(f"[LoRa Script] Successfully sent to {port_name}: '{command_string}'")

    except serial.SerialException as e:
        print(f"[LoRa Script] Error: Could not open or write to serial port {port_name}.")
        print(f"[LoRa Script] Details: {e}")
    except Exception as e:
        print(f"[LoRa Script] An unexpected error occurred: {e}")
    finally:
        # This 'finally' block *always* runs, ensuring we close the port
        if ser and ser.is_open:
            ser.close()
            print(f"[LoRa Script] Serial port {port_name} closed.")

# --- This is the main part that runs when the script is called ---
if __name__ == "__main__":
    # sys.argv is the list of command-line arguments.
    # sys.argv[0] = 'lora_send.py' (the script name)
    # sys.argv[1] = 'person' (the first argument you passed)
    # sys.argv[2] = '75' (the second argument you passed)
    
    if len(sys.argv) == 3:
        label = sys.argv[1]
        confidence = sys.argv[2]
        
        # Format the string to be "label,confidence" e.g., "person,75"
        command_to_send = f"{label},{confidence}"
        command_to_send = command_to_send.encode('utf-8').hex()
        length_cmd = len(command_to_send)
        final_cmd = f"AT+DTRX=1,2,{length_cmd},{command_to_send}"
        send_lora_command(final_cmd)
    else:
        print("[LoRa Script] Error: This script must be called with two arguments (label and confidence).")
        print(f"[LoRa Script] Received: {sys.argv}")
