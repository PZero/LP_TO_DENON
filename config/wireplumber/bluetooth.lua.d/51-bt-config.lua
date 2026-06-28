-- Force A2DP Source auto-connect (receives audio from turntable) and disable suspend timeout
table.insert(bluez_monitor.rules, {
  matches = {
    {
      { "device.name", "matches", "bluez_card.*" },
    },
  },
  apply_properties = {
    ["bluez5.auto-connect"] = "[ hfp_hf hsp_hs a2dp_sink a2dp_source ]",
    ["session.suspend-timeout-seconds"] = 0,
    ["node.pause-on-idle"] = false,
  },
})
