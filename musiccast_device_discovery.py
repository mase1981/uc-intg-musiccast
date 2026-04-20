#!/usr/bin/env python3
"""
Yamaha MusicCast Device Discovery Script v2.1

Captures all device data needed for uc-intg-musiccast v2.0.x development.

:copyright: (c) 2025 by Meir Miyara
:license: MPL-2.0, see LICENSE for more details.
"""

import json
import sys
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode


class MusicCastDiscovery:
    """MusicCast device discovery for uc-intg-musiccast v2.0.x."""

    def __init__(self):
        self.device_ip = None
        self.base_url = None
        self.api_base = None
        self.device_info = {}
        self.data = {
            "timestamp": datetime.now().isoformat(),
            "script_version": "2.1.0",
            "integration_version": "2.0.x",
            "device_info": {},
            "features": {},
            "status": {},
            "play_info": {},
            "preset_info": {},
            "list_info": {},
            "command_tests": {
                "volume": [],
                "playback": [],
                "repeat_shuffle": [],
            },
            "errors": [],
        }

    def print_header(self):
        print("=" * 70)
        print("  Yamaha MusicCast Device Discovery v2.1")
        print("  For uc-intg-musiccast v2.0.x development")
        print("=" * 70)
        print()
        print("This script captures all device data needed to develop and debug")
        print("the MusicCast integration. It tests:")
        print("  - Device info, features, and capabilities")
        print("  - Preset info (favorites/radio stations)")
        print("  - List browsing (net_radio, server, etc.)")
        print("  - Repeat/shuffle command formats (set vs toggle)")
        print("  - Volume, playback command formats")
        print("  - Current status and play info")
        print()
        print("The output JSON file should be sent to the developer.")
        print("=" * 70)
        print()

    def get_device_ip(self):
        while True:
            try:
                ip = input("Enter your MusicCast device IP address: ").strip()
                if not ip:
                    print("  Please enter an IP address")
                    continue
                parts = ip.split(".")
                if len(parts) != 4 or not all(0 <= int(p) <= 255 for p in parts):
                    print("  Invalid IP format. Use format: 192.168.1.100")
                    continue
                self.device_ip = ip
                self.base_url = f"http://{ip}"
                self.api_base = f"{self.base_url}/YamahaExtendedControl/v1"
                print(f"  Using device IP: {ip}")
                return True
            except (ValueError, KeyboardInterrupt):
                if isinstance(sys.exc_info()[1], KeyboardInterrupt):
                    print("\n  Cancelled by user")
                    return False
                print("  Invalid IP address. Use format: 192.168.1.100")

    def make_request(self, endpoint, params=None, timeout=10):
        url = f"{self.api_base}/{endpoint}"
        if params:
            url += "?" + urlencode(params)
        try:
            request = Request(url)
            request.add_header("User-Agent", "MusicCast-Discovery/2.1")
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, json.JSONDecodeError, Exception) as e:
            self.data["errors"].append({"endpoint": endpoint, "params": params, "error": str(e)})
            return None

    def test_connection(self):
        print("\n  Testing connection...")
        response = self.make_request("system/getDeviceInfo")
        if response and response.get("response_code") == 0:
            self.device_info = response
            print(f"  Connected to: {response.get('model_name', 'Unknown')}")
            print(f"  Device ID: {response.get('device_id', 'Unknown')}")
            print(f"  System Version: {response.get('system_version', 'Unknown')}")
            return True
        print("  Connection failed")
        return False

    def collect_device_info(self):
        print("\n[1/7] Device Info...")
        self.data["device_info"] = self.device_info

    def collect_features(self):
        print("[2/7] Features & Capabilities...")
        response = self.make_request("system/getFeatures")
        if response:
            self.data["features"] = response
            zones = response.get("zone", [])
            for z in zones:
                zone_id = z.get("id", "?")
                inputs = z.get("input_list", [])
                programs = z.get("sound_program_list", [])
                funcs = z.get("func_list", [])
                print(f"    Zone '{zone_id}': {len(inputs)} inputs, {len(programs)} sound programs, funcs: {funcs}")
            system = response.get("system", {})
            sys_inputs = system.get("input_list", [])
            print(f"    System: {len(sys_inputs)} input definitions")
        else:
            print("    Failed to get features")

    def collect_status(self):
        print("[3/7] Current Status...")
        response = self.make_request("main/getStatus")
        if response:
            self.data["status"] = response
            print(f"    Power: {response.get('power')}, Input: {response.get('input')}, "
                  f"Volume: {response.get('volume')}/{response.get('max_volume')}, "
                  f"Sound Program: {response.get('sound_program')}")
        else:
            print("    Failed to get status")

    def collect_play_info(self):
        print("[4/7] Play Info...")
        response = self.make_request("netusb/getPlayInfo")
        if response:
            self.data["play_info"] = response
            print(f"    Playback: {response.get('playback')}, "
                  f"Repeat: {response.get('repeat')}, Shuffle: {response.get('shuffle')}")
            track = response.get("track", "")
            artist = response.get("artist", "")
            if track or artist:
                print(f"    Now playing: {artist} - {track}")
        else:
            print("    Failed to get play info")

    def collect_preset_info(self):
        print("[5/7] Preset Info (Favorites)...")
        response = self.make_request("netusb/getPresetInfo")
        if response:
            self.data["preset_info"] = response
            named = 0
            for key, value in response.items():
                if key == "response_code":
                    continue
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and item.get("text", "").strip():
                            named += 1
                        elif isinstance(item, list):
                            for sub in item:
                                if isinstance(sub, dict) and sub.get("text", "").strip():
                                    named += 1
            print(f"    Found {named} named presets")
        else:
            print("    Failed to get preset info")

    def collect_list_info(self):
        print("[6/7] List Browsing (net_radio, server, etc.)...")
        input_sources_to_test = ["net_radio", "server", "usb", "bluetooth", "spotify", "tidal", "deezer", "qobuz"]

        features = self.data.get("features", {})
        available_inputs = []
        for z in features.get("zone", []):
            if z.get("id") == "main":
                available_inputs = z.get("input_list", [])
                break

        sources_to_test = [s for s in input_sources_to_test if s in available_inputs]
        if not sources_to_test:
            sources_to_test = ["net_radio"]

        list_results = {}
        for source in sources_to_test:
            print(f"    Testing getListInfo for '{source}'...")

            result = {"source": source, "attempts": []}

            response = self.make_request("netusb/getListInfo", {"input": source, "index": 0, "size": 8, "lang": "en"})
            result["attempts"].append({
                "params": {"input": source, "index": 0, "size": 8, "lang": "en"},
                "response": response,
            })
            if response and response.get("response_code") == 0:
                items = response.get("list_info", response.get("items", []))
                print(f"      With input param: OK, {len(items) if isinstance(items, list) else '?'} items")
            else:
                code = response.get("response_code", "N/A") if response else "N/A"
                print(f"      With input param: error code {code}")

            response2 = self.make_request("netusb/getListInfo", {"index": 0, "size": 8, "lang": "en"})
            result["attempts"].append({
                "params": {"index": 0, "size": 8, "lang": "en"},
                "response": response2,
            })
            if response2 and response2.get("response_code") == 0:
                items = response2.get("list_info", response2.get("items", []))
                print(f"      Without input param: OK, {len(items) if isinstance(items, list) else '?'} items")
            else:
                code = response2.get("response_code", "N/A") if response2 else "N/A"
                print(f"      Without input param: error code {code}")

            list_results[source] = result
            time.sleep(0.3)

        self.data["list_info"] = list_results

    def test_commands(self):
        print("[7/7] Testing Command Formats...")

        print("  Repeat/Shuffle commands:")
        repeat_shuffle_tests = [
            ("netusb/setRepeat", {"repeat": "off"}, "setRepeat repeat=off"),
            ("netusb/setRepeat", {"repeat": "one"}, "setRepeat repeat=one"),
            ("netusb/setRepeat", {"repeat": "all"}, "setRepeat repeat=all"),
            ("netusb/setShuffle", {"shuffle": "off"}, "setShuffle shuffle=off"),
            ("netusb/setShuffle", {"shuffle": "on"}, "setShuffle shuffle=on"),
            ("netusb/toggleRepeat", None, "toggleRepeat (no params)"),
            ("netusb/toggleShuffle", None, "toggleShuffle (no params)"),
        ]
        for endpoint, params, label in repeat_shuffle_tests:
            response = self.make_request(endpoint, params)
            code = response.get("response_code", "N/A") if response else "N/A"
            status = "OK" if code == 0 else f"error {code}"
            print(f"    {label}: {status}")
            self.data["command_tests"]["repeat_shuffle"].append({
                "endpoint": endpoint, "params": params, "label": label,
                "response_code": code, "works": code == 0,
            })
            time.sleep(0.3)

        print("  Volume commands:")
        volume_tests = [
            ("main/setVolume", {"volume": "up", "step": 1}, "volume=up&step=1"),
            ("main/setVolume", {"volume": "down", "step": 1}, "volume=down&step=1"),
            ("main/setVolume", {"step": 1}, "step=1"),
            ("main/setVolume", {"step": -1}, "step=-1"),
        ]
        for endpoint, params, label in volume_tests:
            response = self.make_request(endpoint, params)
            code = response.get("response_code", "N/A") if response else "N/A"
            status = "OK" if code == 0 else f"error {code}"
            print(f"    {label}: {status}")
            self.data["command_tests"]["volume"].append({
                "endpoint": endpoint, "params": params, "label": label,
                "response_code": code, "works": code == 0,
            })
            time.sleep(0.3)

        print("  Playback commands:")
        playback_tests = [
            ("netusb/setPlayback", {"playback": "toggle"}, "playback=toggle"),
            ("netusb/setPlayback", {"playback": "play"}, "playback=play"),
            ("netusb/setPlayback", {"playback": "pause"}, "playback=pause"),
            ("netusb/setPlayback", {"playback": "stop"}, "playback=stop"),
        ]
        for endpoint, params, label in playback_tests:
            response = self.make_request(endpoint, params)
            code = response.get("response_code", "N/A") if response else "N/A"
            status = "OK" if code == 0 else f"error {code}"
            print(f"    {label}: {status}")
            self.data["command_tests"]["playback"].append({
                "endpoint": endpoint, "params": params, "label": label,
                "response_code": code, "works": code == 0,
            })
            time.sleep(0.3)

    def save_results(self):
        print("\n  Saving results...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model = self.device_info.get("model_name", "Unknown").replace(" ", "_")
        filename = f"musiccast_discovery_{model}_{timestamp}.json"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            print(f"  Saved: {filename}")
            return filename
        except Exception as e:
            print(f"  Error saving: {e}")
            return None

    def print_summary(self):
        print("\n" + "=" * 70)
        print("  SUMMARY")
        print("=" * 70)

        rs = self.data["command_tests"].get("repeat_shuffle", [])
        set_works = any(t["works"] for t in rs if "set" in t["endpoint"].lower() and "toggle" not in t["endpoint"].lower())
        toggle_works = any(t["works"] for t in rs if "toggle" in t["endpoint"].lower())
        print(f"\n  Repeat/Shuffle:")
        print(f"    setRepeat/setShuffle:     {'supported' if set_works else 'NOT supported'}")
        print(f"    toggleRepeat/toggleShuffle: {'supported' if toggle_works else 'NOT supported'}")

        presets = self.data.get("preset_info", {})
        named = 0
        for key, value in presets.items():
            if key == "response_code":
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and item.get("text", "").strip():
                        named += 1
                    elif isinstance(item, list):
                        for sub in item:
                            if isinstance(sub, dict) and sub.get("text", "").strip():
                                named += 1
        print(f"\n  Presets: {named} named presets found")

        list_info = self.data.get("list_info", {})
        for source, result in list_info.items():
            attempts = result.get("attempts", [])
            any_works = any(
                a.get("response", {}).get("response_code") == 0 if a.get("response") else False
                for a in attempts
            )
            print(f"  List browsing '{source}': {'supported' if any_works else 'NOT supported'}")

        print(f"\n  Errors encountered: {len(self.data['errors'])}")
        print()
        print("  Please send the JSON file to the developer for analysis.")
        print("=" * 70)

    def run(self):
        self.print_header()
        if not self.get_device_ip():
            return False
        if not self.test_connection():
            print("\n  Cannot connect to device. Check IP and connectivity.")
            return False

        self.collect_device_info()
        self.collect_features()
        self.collect_status()
        self.collect_play_info()
        self.collect_preset_info()
        self.collect_list_info()
        self.test_commands()

        filename = self.save_results()
        self.print_summary()

        if filename:
            print(f"\n  Output file: {filename}")
            return True
        return False


def main():
    try:
        discovery = MusicCastDiscovery()
        success = discovery.run()
        input("\nPress Enter to exit...")
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n  Unexpected error: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
