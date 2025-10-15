#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WiFi??????
"""

import re

class WifiInfoParser:
    """WiFi?????"""
    
    def __init__(self):
        pass
    
    def parse_wifi(self, raw_wifi):
        """??WiFi??"""
        try:
            # ??WiFi????
            if "WifiState 0" in raw_wifi:
                return {"connected": False}
            
            # ???????WiFi??
            current_ssid_match = re.search(r"current SSID\(s\):\{iface=wlan0,ssid=\"([^\"]*)\"\}", raw_wifi)
            if not current_ssid_match:
                return {"connected": False}
            
            ssid = current_ssid_match.group(1)
            if not ssid or ssid == "<unknown ssid>":
                return {"connected": False}
            
            # ?????SSID?mWifiInfo?
            lines = raw_wifi.split("\n")
            wifi_info_line = None
            for line in lines:
                if f"mWifiInfo SSID: \"{ssid}\"" in line:
                    wifi_info_line = line
                    break
            
            if not wifi_info_line:
                return {"connected": False}
            
            # ???????
            bssid_match = re.search(r"BSSID: ([^,]+)", wifi_info_line)
            rssi_match = re.search(r"RSSI: (-?\d+)", wifi_info_line)
            freq_match = re.search(r"Frequency: (\d+)MHz", wifi_info_line)
            
            if not (bssid_match and rssi_match and freq_match):
                return {"connected": False}
            
            bssid = bssid_match.group(1)
            rssi = int(rssi_match.group(1))
            freq_mhz = int(freq_match.group(1))
            
            # ????
            if freq_mhz == 0:
                band = ""
            elif 2400 <= freq_mhz <= 2500:
                band = "2.4GHz"
            elif 5000 <= freq_mhz <= 6000:
                band = "5GHz"
            elif 6000 <= freq_mhz <= 7000:
                band = "6GHz"
            else:
                band = f"{freq_mhz}MHz"
            
            # ??????
            connected = "Supplicant state: COMPLETED" in wifi_info_line
            
            return {
                "connected": connected,
                "ssid": ssid,
                "bssid": bssid,
                "rssi": rssi,
                "freqMHz": freq_mhz,
                "band": band
            }
            
        except Exception as e:
            print(f"WiFi????: {e}")
            return {"connected": False}
