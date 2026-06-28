-- Let the turntable initiate AVDTP instead of the Pi (prevents connection refused)
bluez_monitor.rules[1].apply_properties["bluez5.auto-connect"] = "[ hfp_hf hsp_hs a2dp_sink ]"
-- Disable suspend timeout for BT nodes (default is 5s which disconnects idle devices!)
bluez_monitor.rules[2].apply_properties["session.suspend-timeout-seconds"] = 0
bluez_monitor.rules[2].apply_properties["node.pause-on-idle"] = false
