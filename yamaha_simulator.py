#!/usr/bin/env python3
"""
Standalone Yamaha MusicCast Simulator.

A simple HTTP server that mimics Yamaha MusicCast API responses
for testing the integration without physical hardware.

Run this in a separate terminal while developing the integration.
"""

import json
import logging
import time
from datetime import datetime
from threading import Lock
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread-safe state management
state_lock = Lock()

# Simulated device state
device_state = {
    "power": "on",
    "volume": 25,
    "max_volume": 100,
    "mute": False,
    "input": "spotify",
    "sound_program": "stereo"
}

# Simulated media state
media_state = {
    "playback": "play",
    "repeat": "off",
    "shuffle": "off",
    "artist": "Yamaha Test Artist",
    "album": "Integration Test Album", 
    "track": "MusicCast Demo Song",
    "play_time": 45,
    "total_time": 180,
    "albumart_url": "https://via.placeholder.com/300x300/1a1a1a/ffffff?text=MusicCast"
}

@app.route('/')
def root():
    return jsonify({
        "message": "Yamaha MusicCast Simulator",
        "device_id": "SIM001122",
        "model": "YAS-209-SIM",
        "endpoints": [
            "/YamahaExtendedControl/v1/system/getDeviceInfo",
            "/YamahaExtendedControl/v1/system/getFeatures",
            "/YamahaExtendedControl/v1/main/getStatus",
            "/YamahaExtendedControl/v1/main/setPower?power=on|standby|toggle",
            "/YamahaExtendedControl/v1/main/setVolume?volume=0-100",
            "/YamahaExtendedControl/v1/main/setMute?enable=true|false",
            "/YamahaExtendedControl/v1/main/setInput?input=hdmi|analog|bluetooth|spotify",
            "/YamahaExtendedControl/v1/netusb/getPlayInfo",
            "/YamahaExtendedControl/v1/netusb/setPlayback?playback=play|pause|stop|toggle|next|previous",
            "/YamahaExtendedControl/v1/netusb/setRepeat?repeat=off|one|all",
            "/YamahaExtendedControl/v1/netusb/setShuffle?shuffle=off|on"
        ]
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "device_id": "SIM001122"})

# System API endpoints
@app.route('/YamahaExtendedControl/v1/system/getDeviceInfo')
def get_device_info():
    return jsonify({
        "response_code": 0,
        "model_name": "YAS-209-SIM",
        "destination": "US",
        "device_id": "SIM001122",
        "system_id": "12345678",
        "system_version": "1.70",
        "api_version": "1.17"
    })

@app.route('/YamahaExtendedControl/v1/system/getFeatures')
def get_features():
    return jsonify({
        "response_code": 0,
        "system": {
            "func_list": ["wired_lan", "wireless_lan", "extend"],
            "zone_num": 1,
            "input_list": [
                {"id": "hdmi", "distribution_enable": True, "rename_enable": True, "account_enable": False},
                {"id": "analog", "distribution_enable": True, "rename_enable": True, "account_enable": False},
                {"id": "bluetooth", "distribution_enable": True, "rename_enable": False, "account_enable": False},
                {"id": "spotify", "distribution_enable": True, "rename_enable": False, "account_enable": True}
            ]
        },
        "zone": [
            {
                "id": "main",
                "func_list": ["power", "volume", "mute", "sound_program"],
                "input_list": ["hdmi", "analog", "bluetooth", "spotify"],
                "sound_program_list": ["stereo", "standard", "surround", "movie", "music"]
            }
        ],
        "netusb": {
            "func_list": ["play_info", "play_control"],
            "preset": {"num": 40}
        }
    })

# Zone control endpoints
@app.route('/YamahaExtendedControl/v1/<zone>/getStatus')
def get_status(zone):
    if zone != "main":
        return jsonify({"response_code": 3})
    
    with state_lock:
        return jsonify({
            "response_code": 0,
            "power": device_state["power"],
            "volume": device_state["volume"],
            "max_volume": device_state["max_volume"],
            "mute": device_state["mute"],
            "input": device_state["input"],
            "sound_program": device_state["sound_program"]
        })

@app.route('/YamahaExtendedControl/v1/<zone>/setPower')
def set_power(zone):
    if zone != "main":
        return jsonify({"response_code": 3})
    
    power = request.args.get('power', 'toggle')
    
    with state_lock:
        if power == "toggle":
            device_state["power"] = "on" if device_state["power"] == "standby" else "standby"
        elif power in ["on", "standby"]:
            device_state["power"] = power
        else:
            return jsonify({"response_code": 4})
        
        # When turning off, stop playback
        if device_state["power"] == "standby":
            media_state["playback"] = "stop"
    
    logger.info(f"Power set to: {device_state['power']}")
    return jsonify({"response_code": 0})

@app.route('/YamahaExtendedControl/v1/<zone>/setVolume')
def set_volume(zone):
    if zone != "main":
        return jsonify({"response_code": 3})
    
    volume = request.args.get('volume')
    step = request.args.get('step')
    
    with state_lock:
        if volume is not None:
            try:
                vol = max(0, min(device_state["max_volume"], int(volume)))
                device_state["volume"] = vol
            except ValueError:
                return jsonify({"response_code": 4})
        elif step is not None:
            try:
                step_val = int(step)
                new_vol = device_state["volume"] + step_val
                device_state["volume"] = max(0, min(device_state["max_volume"], new_vol))
            except ValueError:
                return jsonify({"response_code": 4})
        else:
            return jsonify({"response_code": 4})
    
    logger.info(f"Volume set to: {device_state['volume']}")
    return jsonify({"response_code": 0})

@app.route('/YamahaExtendedControl/v1/<zone>/setMute')
def set_mute(zone):
    if zone != "main":
        return jsonify({"response_code": 3})
    
    enable = request.args.get('enable', '').lower() == 'true'
    
    with state_lock:
        device_state["mute"] = enable
    
    logger.info(f"Mute set to: {device_state['mute']}")
    return jsonify({"response_code": 0})

@app.route('/YamahaExtendedControl/v1/<zone>/setInput')
def set_input(zone):
    if zone != "main":
        return jsonify({"response_code": 3})
    
    input_source = request.args.get('input')
    valid_inputs = ["hdmi", "analog", "bluetooth", "spotify"]
    
    if input_source not in valid_inputs:
        return jsonify({"response_code": 4})
    
    with state_lock:
        device_state["input"] = input_source
        # Change media content based on input
        if input_source == "spotify":
            media_state["artist"] = "Spotify Artist"
            media_state["album"] = "Streaming Album"
            media_state["track"] = "Popular Song"
            media_state["albumart_url"] = "https://via.placeholder.com/300x300/1DB954/ffffff?text=Spotify"
        elif input_source == "bluetooth":
            media_state["artist"] = "Bluetooth Device"
            media_state["album"] = "Phone Music"
            media_state["track"] = "BT Audio"
            media_state["albumart_url"] = "https://via.placeholder.com/300x300/0082FC/ffffff?text=Bluetooth"
        elif input_source == "hdmi":
            media_state["artist"] = "HDMI Source"
            media_state["album"] = "External Device"
            media_state["track"] = "HDMI Audio"
            media_state["albumart_url"] = "https://via.placeholder.com/300x300/FF6B35/ffffff?text=HDMI"
        elif input_source == "analog":
            media_state["artist"] = "Analog Input"
            media_state["album"] = "Line In"
            media_state["track"] = "Analog Audio"
            media_state["albumart_url"] = "https://via.placeholder.com/300x300/4ECDC4/ffffff?text=Analog"
    
    logger.info(f"Input set to: {input_source}")
    return jsonify({"response_code": 0})

@app.route('/YamahaExtendedControl/v1/<zone>/setSoundProgram')
def set_sound_program(zone):
    if zone != "main":
        return jsonify({"response_code": 3})
    
    program = request.args.get('program')
    valid_programs = ["stereo", "standard", "surround", "movie", "music"]
    
    if program not in valid_programs:
        return jsonify({"response_code": 4})
    
    with state_lock:
        device_state["sound_program"] = program
    
    logger.info(f"Sound program set to: {program}")
    return jsonify({"response_code": 0})

# NetUSB/Media endpoints
@app.route('/YamahaExtendedControl/v1/netusb/getPlayInfo')
def get_play_info():
    with state_lock:
        return jsonify({
            "response_code": 0,
            "input": device_state["input"],
            "playback": media_state["playback"],
            "repeat": media_state["repeat"],
            "shuffle": media_state["shuffle"],
            "play_time": media_state["play_time"],
            "total_time": media_state["total_time"],
            "artist": media_state["artist"],
            "album": media_state["album"],
            "track": media_state["track"],
            "albumart_url": media_state["albumart_url"],
            "repeat_available": ["off", "one", "all"],
            "shuffle_available": ["off", "on"]
        })

@app.route('/YamahaExtendedControl/v1/netusb/setPlayback')
def set_playback():
    playback = request.args.get('playback')
    valid_commands = ["play", "pause", "stop", "previous", "next", "toggle"]
    
    if playback not in valid_commands:
        logger.error(f"Invalid playback command received: {playback}")
        return jsonify({"response_code": 4})
    
    with state_lock:
        if playback == "toggle":
            # Handle toggle command properly
            if media_state["playback"] == "play":
                media_state["playback"] = "pause"
            elif media_state["playback"] in ["pause", "stop"]:
                media_state["playback"] = "play"
        elif playback in ["play", "pause", "stop"]:
            media_state["playback"] = playback
        elif playback == "next":
            # Simulate track change
            media_state["play_time"] = 0
            track_num = int(time.time()) % 10 + 1
            media_state["track"] = f"Next Track {track_num}"
            media_state["artist"] = f"Artist {track_num % 5 + 1}"
            if media_state["playback"] != "stop":
                media_state["playback"] = "play"
        elif playback == "previous":
            # Simulate track change
            media_state["play_time"] = 0
            track_num = int(time.time()) % 10 + 1
            media_state["track"] = f"Previous Track {track_num}"
            media_state["artist"] = f"Artist {track_num % 5 + 1}"
            if media_state["playback"] != "stop":
                media_state["playback"] = "play"
    
    logger.info(f"Playback command: {playback} -> current state: {media_state['playback']}")
    return jsonify({"response_code": 0})

@app.route('/YamahaExtendedControl/v1/netusb/setRepeat')
def set_repeat():
    repeat = request.args.get('repeat')
    valid_modes = ["off", "one", "all"]
    
    if repeat not in valid_modes:
        logger.error(f"Invalid repeat mode received: {repeat}")
        return jsonify({"response_code": 4})
    
    with state_lock:
        media_state["repeat"] = repeat
    
    logger.info(f"Repeat set to: {repeat}")
    return jsonify({"response_code": 0})

@app.route('/YamahaExtendedControl/v1/netusb/setShuffle')
def set_shuffle():
    shuffle = request.args.get('shuffle')
    valid_modes = ["off", "on"]
    
    if shuffle not in valid_modes:
        logger.error(f"Invalid shuffle mode received: {shuffle}")
        return jsonify({"response_code": 4})
    
    with state_lock:
        media_state["shuffle"] = shuffle
    
    logger.info(f"Shuffle set to: {shuffle}")
    return jsonify({"response_code": 0})

# Additional endpoints for extended functionality
@app.route('/YamahaExtendedControl/v1/netusb/getPresetInfo')
def get_preset_info():
    """Get preset information."""
    return jsonify({
        "response_code": 0,
        "preset_info": [
            {"input": "spotify", "text": "My Playlist 1", "attribute": 0},
            {"input": "spotify", "text": "My Playlist 2", "attribute": 0},
            {"input": "spotify", "text": "Favorites", "attribute": 0}
        ]
    })

@app.route('/YamahaExtendedControl/v1/netusb/recallPreset')
def recall_preset():
    """Recall a preset."""
    zone = request.args.get('zone', 'main')
    num = request.args.get('num', '1')
    
    try:
        preset_num = int(num)
        if 1 <= preset_num <= 40:
            with state_lock:
                # Simulate preset recall
                media_state["track"] = f"Preset {preset_num} Song"
                media_state["artist"] = f"Preset {preset_num} Artist"
                media_state["album"] = f"Preset {preset_num} Album"
                media_state["playback"] = "play"
                media_state["play_time"] = 0
            
            logger.info(f"Recalled preset {preset_num}")
            return jsonify({"response_code": 0})
        else:
            return jsonify({"response_code": 4})
    except ValueError:
        return jsonify({"response_code": 4})

# Debugging and status endpoints
@app.route('/debug/state')
def debug_state():
    """Get current simulator state for debugging."""
    with state_lock:
        return jsonify({
            "device_state": device_state.copy(),
            "media_state": media_state.copy(),
            "timestamp": datetime.now().isoformat()
        })

@app.route('/debug/reset')
def debug_reset():
    """Reset simulator to initial state."""
    with state_lock:
        device_state.update({
            "power": "on",
            "volume": 25,
            "max_volume": 100,
            "mute": False,
            "input": "spotify",
            "sound_program": "stereo"
        })
        media_state.update({
            "playback": "play",
            "repeat": "off",
            "shuffle": "off",
            "artist": "Yamaha Test Artist",
            "album": "Integration Test Album", 
            "track": "MusicCast Demo Song",
            "play_time": 45,
            "total_time": 180,
            "albumart_url": "https://via.placeholder.com/300x300/1a1a1a/ffffff?text=MusicCast"
        })
    
    logger.info("Simulator state reset to defaults")
    return jsonify({"message": "State reset to defaults", "response_code": 0})

if __name__ == '__main__':
    print("🎵 Yamaha MusicCast Simulator Starting...")
    print("=" * 50)
    print("Device: YAS-209-SIM (SIM001122)")
    print("Listening on: http://localhost:8080")
    print("API Base: http://localhost:8080/YamahaExtendedControl/v1/")
    print()
    print("Initial State: Power ON, Playing Spotify")
    print()
    print("Test Commands:")
    print("  curl http://localhost:8080/YamahaExtendedControl/v1/system/getDeviceInfo")
    print("  curl http://localhost:8080/YamahaExtendedControl/v1/main/getStatus")
    print("  curl 'http://localhost:8080/YamahaExtendedControl/v1/main/setPower?power=on'")
    print("  curl 'http://localhost:8080/YamahaExtendedControl/v1/netusb/setPlayback?playback=toggle'")
    print("  curl 'http://localhost:8080/YamahaExtendedControl/v1/netusb/setRepeat?repeat=one'")
    print("  curl 'http://localhost:8080/YamahaExtendedControl/v1/netusb/setShuffle?shuffle=on'")
    print()
    print("Debug endpoints:")
    print("  curl http://localhost:8080/debug/state")
    print("  curl http://localhost:8080/debug/reset")
    print("=" * 50)
    
    # Install Flask if not available
    try:
        import flask
    except ImportError:
        print("⚠ Flask not installed. Installing...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
        print("✅ Flask installed!")
    
    # Start the simulator
    app.run(host='0.0.0.0', port=8080, debug=False)