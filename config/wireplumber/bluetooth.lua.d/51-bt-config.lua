-- Set auto-connect globally for BlueZ monitor to include a2dp_source (turntable)
bluez_monitor.properties["bluez5.auto-connect"] = "[ hfp_hf hsp_hs a2dp_sink a2dp_source ]"

-- Disable suspend timeout for bluetooth audio nodes
table.insert(bluez_monitor.rules, {
  matches = {
    {
      { "device.name", "matches", "bluez_card.*" },
    },
  },
  apply_properties = {
    ["session.suspend-timeout-seconds"] = 0,
    ["node.pause-on-idle"] = false,
  },
})
