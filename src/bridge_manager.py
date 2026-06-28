import sys
import os
import json
import subprocess
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

STATUS_FILE = "/tmp/lp_status.json"
SOUNDS_DIR = "/usr/local/share/lp_to_denon/sounds"
CONFIG_FILE = "/etc/lp_to_denon.json"

def get_allowed_devices():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return [addr.lower() for addr in data.get("allowed_devices", [])]
        except Exception as e:
            print(f"Error reading config file: {e}")
    return None

def get_mac_from_path(device_path):
    parts = device_path.split("/")
    for part in parts:
        if part.startswith("dev_"):
            return part[4:].replace("_", ":").lower()
    return None

def is_whitelisted(device_path):
    return True


def play_sound(sound_name):
    wav_path = os.path.join(SOUNDS_DIR, f"{sound_name}.wav")
    if os.path.exists(wav_path):
        print(f"Playing sound: {sound_name}")
        # Run pw-play asynchronously to avoid blocking the main D-Bus loop
        subprocess.Popen(["pw-play", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print(f"Sound file not found: {wav_path}")

def write_status(status, device_name=None, device_address=None):
    data = {
        "status": status,
        "device_name": device_name,
        "device_address": device_address
    }
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(data, f)
        # Set file permissions so other users/services can read it
        os.chmod(STATUS_FILE, 0o666)
    except Exception as e:
        print(f"Error writing status file: {e}")

class BluezAgent(dbus.service.Object):
    def __init__(self, bus, path):
        super().__init__(bus, path)

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Release(self):
        print("Agent Release")

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print(f"RequestConfirmation ({device}, {passkey})")
        if not is_whitelisted(device):
            raise dbus.exceptions.DBusException("org.bluez.Error.Rejected")
        print("Auto-Accepting")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print(f"RequestAuthorization ({device})")
        if not is_whitelisted(device):
            raise dbus.exceptions.DBusException("org.bluez.Error.Rejected")
        print("Auto-Accepting")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print(f"AuthorizeService ({device}, {uuid})")
        if not is_whitelisted(device):
            raise dbus.exceptions.DBusException("org.bluez.Error.Rejected")
        print("Auto-Accepting")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print(f"RequestPinCode ({device})")
        if not is_whitelisted(device):
            raise dbus.exceptions.DBusException("org.bluez.Error.Rejected")
        print("Auto-Accepting with '0000'")
        return "0000"

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print(f"RequestPasskey ({device})")
        if not is_whitelisted(device):
            raise dbus.exceptions.DBusException("org.bluez.Error.Rejected")
        print("Auto-Accepting with '000000'")
        return dbus.UInt32(0)

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Cancel(self):
        print("Agent Cancel")

def properties_changed(interface, changed, invalidated, path, bus):
    if interface != "org.bluez.Device1":
        return
    
    mac = get_mac_from_path(path)
    allowed = get_allowed_devices()
    if allowed is not None and mac not in allowed:
        return
    
    if "Connected" in changed:
        is_connected = bool(changed["Connected"])
        print(f"Device properties changed at {path}: Connected={is_connected}")
        
        # Get device properties
        try:
            device_obj = bus.get_object("org.bluez", path)
            device_properties = dbus.Interface(device_obj, "org.freedesktop.DBus.Properties")
            properties = device_properties.GetAll("org.bluez.Device1")
            name = str(properties.get("Name", "Unknown Device"))
            address = str(properties.get("Address", "00:00:00:00:00:00"))
        except Exception as e:
            print(f"Failed to get device info: {e}")
            name = "Unknown Device"
            address = "Unknown Address"

        if is_connected:
            print(f"Connected to {name} [{address}]")
            # Auto-trust the device so it can reconnect automatically
            try:
                device_properties.Set("org.bluez.Device1", "Trusted", dbus.Boolean(True))
                print(f"Device {address} set to Trusted")
            except Exception as e:
                print(f"Failed to set Trusted: {e}")
                
            write_status("connected", name, address)
            play_sound("connected")
        else:
            print(f"Disconnected from {name} [{address}]")
            write_status("searching")
            play_sound("disconnected")

def check_initial_connection(bus):
    try:
        manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()
        allowed = get_allowed_devices()
        for path, interfaces in objects.items():
            if "org.bluez.Device1" in interfaces:
                props = interfaces["org.bluez.Device1"]
                mac = get_mac_from_path(path)
                if allowed is not None and mac not in allowed:
                    continue
                if props.get("Connected"):
                    name = str(props.get("Name", "Unknown Device"))
                    address = str(props.get("Address", "00:00:00:00:00:00"))
                    print(f"Initial state: Already connected to {name} [{address}]")
                    # Ensure it is trusted
                    try:
                        device_obj = bus.get_object("org.bluez", path)
                        device_properties = dbus.Interface(device_obj, "org.freedesktop.DBus.Properties")
                        device_properties.Set("org.bluez.Device1", "Trusted", dbus.Boolean(True))
                    except:
                        pass
                    write_status("connected", name, address)
                    return
    except Exception as e:
        print(f"Error checking initial connections: {e}")
    
    # If no device connected initially
    write_status("searching")

def main():
    print("Starting LP to Denon Bridge Manager...")
    
    # Set up DBus loop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    
    # Initialize status file and play boot chime
    check_initial_connection(bus)
    play_sound("boot")
    
    # Register Bluetooth Agent
    agent_path = "/org/bluez/lp_agent"
    agent = BluezAgent(bus, agent_path)
    
    try:
        manager_obj = bus.get_object("org.bluez", "/org/bluez")
        agent_manager = dbus.Interface(manager_obj, "org.bluez.AgentManager1")
        agent_manager.RegisterAgent(agent_path, "NoInputNoOutput")
        agent_manager.RequestDefaultAgent(agent_path)
        print("Bluetooth Agent registered with capability 'NoInputNoOutput' and set as default.")
    except Exception as e:
        print(f"Failed to register Bluetooth Agent: {e}")
        sys.exit(1)
        
    # Listen to connection properties changes
    bus.add_signal_receiver(
        lambda interface, changed, invalidated, path: properties_changed(interface, changed, invalidated, path, bus),
        bus_name="org.bluez",
        dbus_interface="org.freedesktop.DBus.Properties",
        signal_name="PropertiesChanged",
        path_keyword="path"
    )
    
    print("Bridge Manager is running. Listening for Bluetooth connections...")
    
    # Start GLib main loop
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("Stopping Bridge Manager...")
        try:
            agent_manager.UnregisterAgent(agent_path)
            print("Agent unregistered.")
        except Exception as e:
            print(f"Failed to unregister agent: {e}")
        loop.quit()

if __name__ == "__main__":
    main()
