#!/usr/bin/env python3
"""
Yamaha MusicCast Device Discovery Script


:copyright: (c) 2025 by Meir Miyara
:license: MPL-2.0, see LICENSE for more details.
"""

import json
import socket
import sys
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode


class EnhancedMusicCastDiscovery:
    """Enhanced MusicCast device API discovery with working command detection."""
    
    def __init__(self):
        self.device_ip = None
        self.base_url = None
        self.api_base = None
        self.device_info = {}
        self.discovery_data = {
            "timestamp": datetime.now().isoformat(),
            "script_version": "2.0.0",
            "device_info": {},
            "api_responses": {},
            "working_commands": {},  # New: Store actual working commands
            "command_formats": {},   # New: Store parameter formats that work
            "errors": [],
            "warnings": [],
            "summary": {}
        }
        
    def print_header(self):
        """Print script header."""
        print("=" * 70)
        print("🎵 Enhanced Yamaha MusicCast Device Discovery Script v2.0")
        print("=" * 70)
        print("This enhanced script discovers working command formats")
        print("to improve integration compatibility without guesswork.")
        print()
        print("New features:")
        print("• Tests actual parameter combinations")
        print("• Captures working HTTP command formats")
        print("• Provides copy-paste ready commands")
        print("• Enhanced error analysis")
        print("=" * 70)
        print()
    
    def get_device_ip(self):
        """Get device IP from user input."""
        while True:
            try:
                ip = input("Enter your MusicCast device IP address: ").strip()
                if not ip:
                    print("❌ Please enter an IP address")
                    continue
                
                # Basic IP validation
                parts = ip.split('.')
                if len(parts) != 4:
                    print("❌ Invalid IP format. Use format: 192.168.1.100")
                    continue
                
                for part in parts:
                    if not (0 <= int(part) <= 255):
                        raise ValueError("Invalid IP range")
                
                self.device_ip = ip
                self.base_url = f"http://{ip}"
                self.api_base = f"{self.base_url}/YamahaExtendedControl/v1"
                print(f"✅ Using device IP: {ip}")
                return True
                
            except ValueError:
                print("❌ Invalid IP address. Please use format: 192.168.1.100")
            except KeyboardInterrupt:
                print("\n🛑 Discovery cancelled by user")
                return False
    
    def test_connection(self):
        """Test basic connection to device."""
        print("\n🔍 Testing connection to device...")
        
        try:
            # Test basic HTTP connectivity
            response = self.make_request("system/getDeviceInfo")
            if response and "response_code" in response:
                if response["response_code"] == 0:
                    self.device_info = response
                    print(f"✅ Connected to: {response.get('model_name', 'Unknown Model')}")
                    print(f"   Device ID: {response.get('device_id', 'Unknown')}")
                    print(f"   System Version: {response.get('system_version', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Device returned error code: {response['response_code']}")
                    return False
            else:
                print("❌ Invalid response from device")
                return False
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def make_request(self, endpoint, params=None, timeout=10):
        """Make HTTP request to device API."""
        url = f"{self.api_base}/{endpoint}"
        if params:
            url += "?" + urlencode(params)
        
        try:
            request = Request(url)
            request.add_header('User-Agent', 'Enhanced-MusicCast-Discovery/2.0')
            
            with urlopen(request, timeout=timeout) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
                
        except HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            self.discovery_data["errors"].append({
                "endpoint": endpoint,
                "params": params,
                "error": error_msg,
                "type": "http_error"
            })
            return None
            
        except URLError as e:
            error_msg = f"URL Error: {e.reason}"
            self.discovery_data["errors"].append({
                "endpoint": endpoint,
                "params": params,
                "error": error_msg,
                "type": "url_error"
            })
            return None
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON Decode Error: {e}"
            self.discovery_data["errors"].append({
                "endpoint": endpoint,
                "params": params,
                "error": error_msg,
                "type": "json_error"
            })
            return None
            
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self.discovery_data["errors"].append({
                "endpoint": endpoint,
                "params": params,
                "error": error_msg,
                "type": "unknown_error"
            })
            return None
    
    def test_volume_command_formats(self):
        """Test different volume command parameter formats."""
        print("\n🔊 Testing volume command formats...")
        
        working_formats = []
        
        # Test various volume parameter combinations
        volume_tests = [
            # Standard integration formats
            {"step": 1},
            {"step": -1},
            {"step": 4},
            {"step": -4},
            {"volume": 50},
            
            # R-N803D specific formats (from user report)
            {"volume": "up", "step": 4},
            {"volume": "down", "step": 4},
            {"volume": "up", "step": 1},
            {"volume": "down", "step": 1},
            
            # Other possible formats
            {"direction": "up"},
            {"direction": "down"},
            {"volume": "up"},
            {"volume": "down"},
            {"cmd": "up"},
            {"cmd": "down"},
        ]
        
        for params in volume_tests:
            print(f"  📝 Testing volume params: {params}...", end="")
            response = self.make_request("main/setVolume", params)
            
            if response and response.get("response_code") == 0:
                working_formats.append({
                    "endpoint": "main/setVolume",
                    "params": params,
                    "http_command": f"{self.api_base}/main/setVolume?{urlencode(params)}",
                    "response": response
                })
                print(" ✅")
            else:
                error_code = response.get("response_code", "No response") if response else "No response"
                print(f" ❌ (code: {error_code})")
        
        if working_formats:
            self.discovery_data["working_commands"]["volume"] = working_formats
            print(f"  📊 Found {len(working_formats)} working volume formats")
        else:
            print("  ⚠️  No working volume formats found")
    
    def test_playback_command_formats(self):
        """Test different playback command parameter formats."""
        print("\n▶️ Testing playback command formats...")
        
        working_formats = []
        
        # Test various playback parameter combinations
        playback_tests = [
            # Standard formats
            {"playback": "play"},
            {"playback": "pause"},
            {"playback": "stop"},
            {"playback": "toggle"},
            {"playback": "next"},
            {"playback": "previous"},
            
            # Alternative parameter names
            {"cmd": "play"},
            {"cmd": "pause"},
            {"cmd": "toggle"},
            {"action": "play"},
            {"action": "pause"},
            {"control": "play"},
            {"control": "pause"},
        ]
        
        for params in playback_tests:
            print(f"  📝 Testing playback params: {params}...", end="")
            response = self.make_request("netusb/setPlayback", params)
            
            if response and response.get("response_code") == 0:
                working_formats.append({
                    "endpoint": "netusb/setPlayback",
                    "params": params,
                    "http_command": f"{self.api_base}/netusb/setPlayback?{urlencode(params)}",
                    "response": response
                })
                print(" ✅")
            else:
                error_code = response.get("response_code", "No response") if response else "No response"
                print(f" ❌ (code: {error_code})")
        
        if working_formats:
            self.discovery_data["working_commands"]["playback"] = working_formats
            print(f"  📊 Found {len(working_formats)} working playback formats")
        else:
            print("  ⚠️  No working playback formats found")
    
    def test_repeat_shuffle_formats(self):
        """Test repeat and shuffle command formats."""
        print("\n🔁 Testing repeat/shuffle command formats...")
        
        working_formats = []
        
        # Test repeat commands
        repeat_tests = [
            {"repeat": "off"},
            {"repeat": "one"},
            {"repeat": "all"},
        ]
        
        shuffle_tests = [
            {"shuffle": "off"},
            {"shuffle": "on"},
        ]
        
        # Test repeat
        for params in repeat_tests:
            print(f"  📝 Testing repeat params: {params}...", end="")
            response = self.make_request("netusb/setRepeat", params)
            
            if response and response.get("response_code") == 0:
                working_formats.append({
                    "endpoint": "netusb/setRepeat",
                    "params": params,
                    "http_command": f"{self.api_base}/netusb/setRepeat?{urlencode(params)}",
                    "response": response
                })
                print(" ✅")
            else:
                error_code = response.get("response_code", "No response") if response else "No response"
                print(f" ❌ (code: {error_code})")
        
        # Test shuffle
        for params in shuffle_tests:
            print(f"  📝 Testing shuffle params: {params}...", end="")
            response = self.make_request("netusb/setShuffle", params)
            
            if response and response.get("response_code") == 0:
                working_formats.append({
                    "endpoint": "netusb/setShuffle",
                    "params": params,
                    "http_command": f"{self.api_base}/netusb/setShuffle?{urlencode(params)}",
                    "response": response
                })
                print(" ✅")
            else:
                error_code = response.get("response_code", "No response") if response else "No response"
                print(f" ❌ (code: {error_code})")
        
        # Test toggle endpoints
        toggle_tests = [
            ("netusb/toggleRepeat", {}),
            ("netusb/toggleShuffle", {}),
        ]
        
        for endpoint, params in toggle_tests:
            print(f"  📝 Testing {endpoint}...", end="")
            response = self.make_request(endpoint, params)
            
            if response and response.get("response_code") == 0:
                working_formats.append({
                    "endpoint": endpoint,
                    "params": params,
                    "http_command": f"{self.api_base}/{endpoint}",
                    "response": response
                })
                print(" ✅")
            else:
                error_code = response.get("response_code", "No response") if response else "No response"
                print(f" ❌ (code: {error_code})")
        
        if working_formats:
            self.discovery_data["working_commands"]["repeat_shuffle"] = working_formats
            print(f"  📊 Found {len(working_formats)} working repeat/shuffle formats")
        else:
            print("  ⚠️  No working repeat/shuffle formats found")
    
    def generate_integration_recommendations(self):
        """Generate recommendations for integration enhancement."""
        print("\n💡 Analyzing results for integration recommendations...")
        
        recommendations = {
            "volume_commands": [],
            "playback_commands": [],
            "repeat_shuffle_commands": [],
            "general_recommendations": []
        }
        
        # Volume recommendations
        volume_commands = self.discovery_data["working_commands"].get("volume", [])
        if volume_commands:
            recommendations["volume_commands"] = [
                f"Use: {cmd['http_command']}" for cmd in volume_commands
            ]
        else:
            recommendations["volume_commands"] = [
                "No working volume commands found - device may require specific power state",
                "Try testing with device in different power states (on/standby)"
            ]
        
        # Playback recommendations
        playback_commands = self.discovery_data["working_commands"].get("playback", [])
        if playback_commands:
            recommendations["playback_commands"] = [
                f"Use: {cmd['http_command']}" for cmd in playback_commands
            ]
        else:
            recommendations["playback_commands"] = [
                "No working playback commands found - check device state and input source"
            ]
        
        # Repeat/Shuffle recommendations
        repeat_shuffle_commands = self.discovery_data["working_commands"].get("repeat_shuffle", [])
        if repeat_shuffle_commands:
            recommendations["repeat_shuffle_commands"] = [
                f"Use: {cmd['http_command']}" for cmd in repeat_shuffle_commands
            ]
        
        # General recommendations
        error_rate = len(self.discovery_data["errors"]) / (len(self.discovery_data["api_responses"]) + len(self.discovery_data["errors"])) * 100
        if error_rate > 50:
            recommendations["general_recommendations"].append(
                f"High error rate ({error_rate:.1f}%) - device may have limited API support"
            )
        
        self.discovery_data["integration_recommendations"] = recommendations
    
    def save_results(self):
        """Save enhanced discovery results."""
        print("\n💾 Saving enhanced discovery results...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        device_model = self.device_info.get("model_name", "Unknown").replace(" ", "_")
        
        # Create enhanced report filename
        report_filename = f"enhanced_musiccast_discovery_{device_model}_{timestamp}.json"
        
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(self.discovery_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Enhanced report saved: {report_filename}")
            
            # Create developer-friendly summary
            dev_summary_filename = f"musiccast_integration_guide_{device_model}_{timestamp}.txt"
            with open(dev_summary_filename, 'w', encoding='utf-8') as f:
                f.write("🎵 MusicCast Integration Developer Guide\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"Device: {device_model}\n")
                f.write(f"Discovery Date: {self.discovery_data['timestamp']}\n\n")
                
                # Working commands section
                f.write("🔧 WORKING HTTP COMMANDS:\n")
                f.write("-" * 30 + "\n")
                
                for category, commands in self.discovery_data["working_commands"].items():
                    f.write(f"\n{category.title()} Commands:\n")
                    for cmd in commands:
                        f.write(f"  • {cmd['http_command']}\n")
                
                # Integration recommendations
                f.write(f"\n💡 INTEGRATION RECOMMENDATIONS:\n")
                f.write("-" * 30 + "\n")
                
                for category, recs in self.discovery_data.get("integration_recommendations", {}).items():
                    if recs:
                        f.write(f"\n{category.replace('_', ' ').title()}:\n")
                        for rec in recs:
                            f.write(f"  • {rec}\n")
                
                f.write(f"\n📋 Copy-paste these working commands for integration testing\n")
            
            print(f"✅ Developer guide saved: {dev_summary_filename}")
            
            return report_filename, dev_summary_filename
            
        except Exception as e:
            print(f"❌ Error saving files: {e}")
            return None, None
    
    def run_enhanced_discovery(self):
        """Run enhanced discovery process."""
        self.print_header()
        
        # Get device IP
        if not self.get_device_ip():
            return False
        
        # Test connection
        if not self.test_connection():
            print("\n❌ Cannot connect to device. Please check connectivity.")
            return False
        
        # Store device info
        self.discovery_data["device_info"] = self.device_info
        
        print("\n🚀 Starting enhanced API discovery...")
        print("Testing actual command formats to find what works...")
        
        # Test working command formats
        self.test_volume_command_formats()
        self.test_playback_command_formats()
        self.test_repeat_shuffle_formats()
        
        # Generate recommendations
        self.generate_integration_recommendations()
        
        # Save results
        report_file, guide_file = self.save_results()
        
        if report_file and guide_file:
            print("\n🎉 Enhanced discovery completed!")
            print(f"\n📄 Files created:")
            print(f"  • {report_file} (full discovery data)")
            print(f"  • {guide_file} (developer integration guide)")
            
            working_commands_count = sum(len(cmds) for cmds in self.discovery_data["working_commands"].values())
            print(f"\n📊 Results:")
            print(f"  • Working commands found: {working_commands_count}")
            print(f"  • Ready for integration enhancement")
            
            return True
        else:
            print("\n❌ Enhanced discovery completed but failed to save results")
            return False


def main():
    """Main entry point."""
    try:
        discovery = EnhancedMusicCastDiscovery()
        success = discovery.run_enhanced_discovery()
        
        if success:
            input("\nPress Enter to exit...")
        else:
            input("\nPress Enter to exit...")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Enhanced discovery cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please report this error to the developer")
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()