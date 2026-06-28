import subprocess
import threading
import time
import sys
import os

# We monitor both TV (0) and Audio System (5)
DEVICES_TO_MONITOR = [0, 5]
POLL_INTERVAL = 20  # Poll every 20 seconds

current_power_state = "unknown"  # Can be "on", "standby", "unknown"
cec_process = None

def run_command(cmd):
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Executed command: {cmd}")
    except Exception as e:
        print(f"Failed to execute command '{cmd}': {e}", file=sys.stderr)

def set_system_state(state):
    global current_power_state
    if current_power_state == state:
        return
        
    print(f"System transitioning from {current_power_state} to {state}")
    current_power_state = state
    
    if state == "on":
        # Turn on HDMI display
        run_command("vcgencmd display_power 1")
        # Ensure HDMI output is active in X11/DPMS if running
        run_command("export DISPLAY=:0 && xset dpms force on || true")
        # Turn on Bluetooth controller and make it discoverable
        run_command("bluetoothctl power on")
        run_command("bluetoothctl discoverable on")
        run_command("bluetoothctl pairable on")
    elif state == "standby":
        # Turn off Bluetooth to prevent giradischi from auto-connecting in standby
        run_command("bluetoothctl discoverable off")
        run_command("bluetoothctl power off")
        # Turn off HDMI display to save power/signal
        run_command("vcgencmd display_power 0")
        run_command("export DISPLAY=:0 && xset dpms force off || true")

def poll_cec_devices(proc):
    """Periodically writes poll commands to cec-client stdin"""
    while proc.poll() is None:
        for dev in DEVICES_TO_MONITOR:
            try:
                proc.stdin.write(f"pow {dev}\n")
                proc.stdin.flush()
            except Exception as e:
                print(f"Error writing to cec-client: {e}", file=sys.stderr)
        time.sleep(POLL_INTERVAL)

def parse_cec_output(proc):
    global current_power_state
    
    # Store recent power states of devices
    device_states = {dev: "unknown" for dev in DEVICES_TO_MONITOR}
    
    for line in iter(proc.stdout.readline, ''):
        line = line.strip()
        if not line:
            continue
            
        print(f"[CEC-LOG] {line}")
        
        # Parse power status responses, e.g.:
        # "power status: on" or "power status: standby"
        # Often preceded by device info in the logs
        lower_line = line.lower()
        
        # Look for explicit standby broadcasts or direct commands
        # e.g., ">> 05:36" (device 5 to standby) or "<< TV (0) -> standby"
        if "-> standby" in lower_line or ">> 05:36" in lower_line or ">> 00:36" in lower_line:
            print("Detected standby broadcast/event.")
            set_system_state("standby")
            continue
            
        if "-> on" in lower_line or ">> 05:04" in lower_line or ">> 00:04" in lower_line:
            print("Detected power-on broadcast/event.")
            set_system_state("on")
            continue
            
        # Parse responses to our "pow X" polls
        # Example format: "power status: on"
        # The preceding lines usually show which device is being queried
        # Or it looks like: "Device 5: power status: standby" or similar depending on cec-client version
        if "power status:" in lower_line:
            # We look at the status string
            status = "unknown"
            if "power status: on" in lower_line:
                status = "on"
            elif "power status: standby" in lower_line or "power status: 'standby'" in lower_line:
                status = "standby"
                
            # If any queried device (TV or Audio System) is "on", we consider the system active.
            # If both are in "standby", we standby.
            # Let's extract the device ID if present in the line (e.g. "Device 5: power status: on")
            # If no device ID, we assume it's the TV or Audio receiver we just polled
            dev_id = None
            for dev in DEVICES_TO_MONITOR:
                if f"device {dev}:" in lower_line or f"({dev}):" in lower_line:
                    dev_id = dev
                    break
            
            if status != "unknown":
                if dev_id is not None:
                    device_states[dev_id] = status
                else:
                    # Generic response, apply to all for safety or treat as active if "on"
                    if status == "on":
                        set_system_state("on")
                        continue
                
                # Check aggregate state
                states_list = [device_states[d] for d in DEVICES_TO_MONITOR if device_states[d] != "unknown"]
                if "on" in states_list:
                    set_system_state("on")
                elif len(states_list) > 0 and all(s == "standby" for s in states_list):
                    set_system_state("standby")

def main():
    global cec_process
    print("Starting LP to Denon CEC Monitor...")
    
    # Initialize HDMI display ON at boot
    run_command("vcgencmd display_power 1")
    run_command("bluetoothctl power on")
    run_command("bluetoothctl discoverable on")
    
    # Start cec-client
    # -d 1: only traffic and errors
    # -m: do not auto-configure as active source (we just want to monitor)
    try:
        cec_process = subprocess.Popen(
            ["cec-client", "-d", "1"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    except Exception as e:
        print(f"Failed to start cec-client: {e}. Is cec-utils installed?", file=sys.stderr)
        sys.exit(1)
        
    # Start thread to parse stdout
    parser_thread = threading.Thread(target=parse_cec_output, args=(cec_process,), daemon=True)
    parser_thread.start()
    
    # Start thread to poll devices
    poll_thread = threading.Thread(target=poll_cec_devices, args=(cec_process,), daemon=True)
    poll_thread.start()
    
    print("CEC Monitor running. Press Ctrl+C to stop.")
    
    try:
        while cec_process.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping CEC Monitor...")
        if cec_process:
            cec_process.terminate()
            cec_process.wait()

if __name__ == "__main__":
    main()
