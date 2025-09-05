#!/usr/bin/env python3
"""
Yamaha MusicCast Device Discovery Script

This script connects to your MusicCast device and exports comprehensive
API data to help improve the integration. No external dependencies required.

Usage:
    python musiccast_device_discovery.py

The script will:
1. Ask for your MusicCast device IP address
2. Connect and query all available API endpoints
3. Generate a detailed report file
4. Create an export file you can share with the developer

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


class MusicCastDiscovery:
    """Comprehensive MusicCast device API discovery."""
    
    def __init__(self):
        self.device_ip = None
        self.base_url = None
        self.api_base = None
        self.device_info = {}
        self.discovery_data = {
            "timestamp": datetime.now().isoformat(),
            "script_version": "1.0.0",
            "device_info": {},
            "api_responses": {},
            "errors": [],
            "warnings": [],
            "summary": {}
        }
        
    def print_header(self):
        """Print script header."""
        print("=" * 70)
        print("🎵 Yamaha MusicCast Device Discovery Script")
        print("=" * 70)
        print("This script will connect to your MusicCast device and")
        print("export comprehensive API data to help improve the integration.")
        print()
        print("What this script does:")
        print("• Connects to your MusicCast device")
        print("• Queries all available API endpoints")
        print("• Tests device capabilities and features")
        print("• Generates a detailed report for developers")
        print("• Creates an export file you can share")
        print()
        print("Requirements:")
        print("• Python 3.6+ (already installed)")
        print("• MusicCast device on same network")
        print("• Device IP address")
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
            request.add_header('User-Agent', 'MusicCast-Discovery/1.0')
            
            with urlopen(request, timeout=timeout) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
                
        except HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            self.discovery_data["errors"].append({
                "endpoint": endpoint,
                "error": error_msg,
                "type": "http_error"
            })
            return None
            
        except URLError as e:
            error_msg = f"URL Error: {e.reason}"
            self.discovery_data["errors"].append({
                "endpoint": endpoint,
                "error": error_msg,
                "type": "url_error"
            })
            return None
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON Decode Error: {e}"
            self.discovery_data["errors"].append({
                "endpoint": endpoint,
                "error": error_msg,
                "type": "json_error"
            })
            return None
            
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self.discovery_data["errors"].append({
                "endpoint": endpoint,
                "error": error_msg,
                "type": "unknown_error"
            })
            return None
    
    def discover_system_endpoints(self):
        """Discover system-level API endpoints."""
        print("\n🔍 Discovering system endpoints...")
        
        system_endpoints = [
            "system/getDeviceInfo",
            "system/getFeatures",
            "system/getNetworkStatus",
            "system/getFuncStatus",
            "system/setAutoPowerStandby",
            "system/getLocationInfo",
            "system/sendIrCode",
            "system/setWiredLan",
            "system/setWirelessLan",
            "system/setWirelessDirect",
            "system/setIpSettings",
            "system/setNetworkName",
            "system/getAccountStatus",
            "system/switchAccount",
            "system/getMusicCastStatus",
            "system/getSignalInfo",
            "system/setSpeakerPattern",
            "system/getSpeakerPattern"
        ]
        
        for endpoint in system_endpoints:
            short_name = endpoint.split('/')[-1]
            print(f"  📡 Testing {short_name}...", end="")
            
            response = self.make_request(endpoint)
            if response:
                self.discovery_data["api_responses"][endpoint] = response
                print(" ✅")
            else:
                print(" ❌")
    
    def discover_zone_endpoints(self):
        """Discover zone-specific API endpoints."""
        print("\n🔍 Discovering zone endpoints...")
        
        # Common zones to test
        zones = ["main", "zone2", "zone3", "zone4"]
        
        zone_endpoints = [
            "getStatus",
            "getSignalInfo", 
            "setSleep",
            "setPower",
            "setVolume",
            "setMute",
            "setInput",
            "setSoundProgram",
            "setPureDirect",
            "setEnhancer",
            "setToneControl",
            "setEqualizer",
            "setBalance",
            "setSubwooferVolume",
            "setBassExtension",
            "setClearVoice",
            "set3dSurround",
            "setDirectMode",
            "setExtraBass",
            "setAdaptiveDrc",
            "setBassBoost",
            "setMusicBoost",
            "setSurroundDecoder",
            "setDtsDialog",
            "setContentsDisplay",
            "setPartyMode",
            "getPresetInfo",
            "recallPreset",
            "storePreset",
            "setAutoPreset",
            "setSpeaker",
            "setDimmer",
            "setZoneBgm"
        ]
        
        for zone in zones:
            print(f"  🎛️  Testing zone: {zone}")
            zone_responses = {}
            
            for endpoint in zone_endpoints:
                full_endpoint = f"{zone}/{endpoint}"
                response = self.make_request(full_endpoint)
                if response:
                    zone_responses[endpoint] = response
            
            if zone_responses:
                self.discovery_data["api_responses"][f"zone_{zone}"] = zone_responses
                print(f"    ✅ Found {len(zone_responses)} working endpoints")
            else:
                print(f"    ❌ No working endpoints found")
    
    def discover_netusb_endpoints(self):
        """Discover network/USB media endpoints."""
        print("\n🔍 Discovering NetUSB/Media endpoints...")
        
        netusb_endpoints = [
            "netusb/getPlayInfo",
            "netusb/setPlayback",
            "netusb/setRepeat", 
            "netusb/setShuffle",
            "netusb/getListInfo",
            "netusb/setListControl",
            "netusb/setSearchString",
            "netusb/getSearchResult",
            "netusb/getRecentInfo",
            "netusb/clearRecentInfo",
            "netusb/setRecentControl",
            "netusb/getPresetInfo",
            "netusb/recallPreset",
            "netusb/storePreset",
            "netusb/managePlay",
            "netusb/getSettings",
            "netusb/setSettings",
            "netusb/getServiceInfo",
            "netusb/setServiceControl",
            "netusb/getAccountStatus",
            "netusb/switchAccount",
            "netusb/getMcPlaylist",
            "netusb/setMcPlaylist",
            "netusb/setBrowseFilter",
            "netusb/getPlayQueue",
            "netusb/setPlayQueue"
        ]
        
        working_endpoints = 0
        for endpoint in netusb_endpoints:
            short_name = endpoint.split('/')[-1]
            print(f"  🎵 Testing {short_name}...", end="")
            
            response = self.make_request(endpoint)
            if response:
                self.discovery_data["api_responses"][endpoint] = response
                working_endpoints += 1
                print(" ✅")
            else:
                print(" ❌")
        
        print(f"  📊 NetUSB endpoints: {working_endpoints}/{len(netusb_endpoints)} working")
    
    def discover_tuner_endpoints(self):
        """Discover tuner-specific endpoints."""
        print("\n🔍 Discovering Tuner endpoints...")
        
        tuner_endpoints = [
            "tuner/getPlayInfo",
            "tuner/setFreq",
            "tuner/recallPreset",
            "tuner/storePreset",
            "tuner/setDabService",
            "tuner/getDabServiceList",
            "tuner/setFmFreq",
            "tuner/setAmFreq",
            "tuner/startDabInitialScan",
            "tuner/startDabAutoPreset",
            "tuner/setDabPreset",
            "tuner/getDabPresetInfo"
        ]
        
        working_endpoints = 0
        for endpoint in tuner_endpoints:
            short_name = endpoint.split('/')[-1]
            print(f"  📻 Testing {short_name}...", end="")
            
            response = self.make_request(endpoint)
            if response:
                self.discovery_data["api_responses"][endpoint] = response
                working_endpoints += 1
                print(" ✅")
            else:
                print(" ❌")
        
        print(f"  📊 Tuner endpoints: {working_endpoints}/{len(tuner_endpoints)} working")
    
    def discover_clock_endpoints(self):
        """Discover clock/timer endpoints."""
        print("\n🔍 Discovering Clock/Timer endpoints...")
        
        clock_endpoints = [
            "clock/getSettings",
            "clock/setSettings",
            "clock/setDateAndTime",
            "clock/setClockFormat",
            "clock/setAlarmSettings",
            "clock/getAlarmSettings",
            "clock/setSleepTimer",
            "clock/getSleepTimer"
        ]
        
        working_endpoints = 0
        for endpoint in clock_endpoints:
            short_name = endpoint.split('/')[-1]
            print(f"  ⏰ Testing {short_name}...", end="")
            
            response = self.make_request(endpoint)
            if response:
                self.discovery_data["api_responses"][endpoint] = response
                working_endpoints += 1
                print(" ✅")
            else:
                print(" ❌")
        
        print(f"  📊 Clock endpoints: {working_endpoints}/{len(clock_endpoints)} working")
    
    def test_special_features(self):
        """Test device-specific special features."""
        print("\n🔍 Testing special device features...")
        
        # Test MusicCast link capabilities
        print("  🔗 Testing MusicCast Link...")
        link_response = self.make_request("dist/getDistributionInfo")
        if link_response:
            self.discovery_data["api_responses"]["musiccast_link"] = link_response
            print("    ✅ MusicCast Link supported")
        else:
            print("    ❌ MusicCast Link not available")
        
        # Test CD player if available
        print("  💿 Testing CD player...")
        cd_response = self.make_request("cd/getPlayInfo")
        if cd_response:
            self.discovery_data["api_responses"]["cd_player"] = cd_response
            print("    ✅ CD player detected")
        else:
            print("    ❌ CD player not available")
        
        # Test streaming services
        print("  🌐 Testing streaming services...")
        streaming_services = ["spotify", "pandora", "sirius", "tidal", "deezer", "amazon_music"]
        detected_services = []
        
        for service in streaming_services:
            # Try to get service-specific info
            response = self.make_request(f"netusb/getAccountStatus", {"input": service})
            if response and response.get("response_code") == 0:
                detected_services.append(service)
        
        if detected_services:
            self.discovery_data["streaming_services"] = detected_services
            print(f"    ✅ Detected services: {', '.join(detected_services)}")
        else:
            print("    ❌ No streaming services detected")
    
    def analyze_capabilities(self):
        """Analyze device capabilities based on discovered data."""
        print("\n📊 Analyzing device capabilities...")
        
        capabilities = {
            "zones": [],
            "inputs": [],
            "sound_programs": [],
            "streaming_services": [],
            "special_features": [],
            "api_coverage": {}
        }
        
        # Analyze zones
        for key in self.discovery_data["api_responses"]:
            if key.startswith("zone_"):
                zone_name = key.replace("zone_", "")
                capabilities["zones"].append(zone_name)
        
        # Analyze features from getFeatures response
        features_response = self.discovery_data["api_responses"].get("system/getFeatures")
        if features_response:
            if "zone" in features_response:
                for zone in features_response["zone"]:
                    if "input_list" in zone:
                        capabilities["inputs"].extend(zone["input_list"])
                    if "sound_program_list" in zone:
                        capabilities["sound_programs"].extend(zone["sound_program_list"])
            
            if "system" in features_response:
                if "input_list" in features_response["system"]:
                    for input_info in features_response["system"]["input_list"]:
                        if isinstance(input_info, dict) and "id" in input_info:
                            capabilities["inputs"].append(input_info["id"])
        
        # Count API coverage
        total_endpoints = len(self.discovery_data["api_responses"])
        total_errors = len(self.discovery_data["errors"])
        
        capabilities["api_coverage"] = {
            "working_endpoints": total_endpoints,
            "failed_endpoints": total_errors,
            "success_rate": f"{(total_endpoints / (total_endpoints + total_errors) * 100):.1f}%" if (total_endpoints + total_errors) > 0 else "0%"
        }
        
        # Remove duplicates
        capabilities["inputs"] = list(set(capabilities["inputs"]))
        capabilities["sound_programs"] = list(set(capabilities["sound_programs"]))
        
        self.discovery_data["capabilities"] = capabilities
        
        print(f"  🎛️  Zones detected: {len(capabilities['zones'])}")
        print(f"  🔌 Inputs available: {len(capabilities['inputs'])}")
        print(f"  🎵 Sound programs: {len(capabilities['sound_programs'])}")
        print(f"  📡 API coverage: {capabilities['api_coverage']['success_rate']}")
    
    def generate_summary(self):
        """Generate discovery summary."""
        device_info = self.discovery_data["api_responses"].get("system/getDeviceInfo", {})
        
        summary = {
            "device_model": device_info.get("model_name", "Unknown"),
            "device_id": device_info.get("device_id", "Unknown"),
            "system_version": device_info.get("system_version", "Unknown"),
            "api_version": device_info.get("api_version", "Unknown"),
            "discovery_timestamp": self.discovery_data["timestamp"],
            "total_endpoints_tested": len(self.discovery_data["api_responses"]) + len(self.discovery_data["errors"]),
            "successful_endpoints": len(self.discovery_data["api_responses"]),
            "failed_endpoints": len(self.discovery_data["errors"]),
            "capabilities_found": len(self.discovery_data.get("capabilities", {}).get("inputs", [])),
            "zones_detected": len(self.discovery_data.get("capabilities", {}).get("zones", [])),
        }
        
        self.discovery_data["summary"] = summary
    
    def save_results(self):
        """Save discovery results to files."""
        print("\n💾 Saving discovery results...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        device_model = self.discovery_data["summary"].get("device_model", "Unknown").replace(" ", "_")
        
        # Create detailed report filename
        report_filename = f"musiccast_discovery_{device_model}_{timestamp}.json"
        
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(self.discovery_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Detailed report saved: {report_filename}")
            
            # Create user-friendly summary
            summary_filename = f"musiccast_summary_{device_model}_{timestamp}.txt"
            with open(summary_filename, 'w', encoding='utf-8') as f:
                f.write("🎵 Yamaha MusicCast Device Discovery Summary\n")
                f.write("=" * 50 + "\n\n")
                
                summary = self.discovery_data["summary"]
                f.write(f"Device Model: {summary['device_model']}\n")
                f.write(f"Device ID: {summary['device_id']}\n")
                f.write(f"System Version: {summary['system_version']}\n")
                f.write(f"API Version: {summary['api_version']}\n")
                f.write(f"Discovery Date: {summary['discovery_timestamp']}\n\n")
                
                f.write("📊 API Discovery Results:\n")
                f.write(f"• Total endpoints tested: {summary['total_endpoints_tested']}\n")
                f.write(f"• Successful endpoints: {summary['successful_endpoints']}\n")
                f.write(f"• Failed endpoints: {summary['failed_endpoints']}\n")
                f.write(f"• Success rate: {(summary['successful_endpoints']/summary['total_endpoints_tested']*100):.1f}%\n\n")
                
                capabilities = self.discovery_data.get("capabilities", {})
                if capabilities:
                    f.write("🎛️  Device Capabilities:\n")
                    f.write(f"• Zones: {', '.join(capabilities.get('zones', []))}\n")
                    f.write(f"• Inputs: {', '.join(capabilities.get('inputs', []))}\n")
                    f.write(f"• Sound Programs: {len(capabilities.get('sound_programs', []))} available\n\n")
                
                if self.discovery_data.get("streaming_services"):
                    f.write(f"🌐 Streaming Services: {', '.join(self.discovery_data['streaming_services'])}\n\n")
                
                f.write("📁 Files Generated:\n")
                f.write(f"• Detailed report: {report_filename}\n")
                f.write(f"• This summary: {summary_filename}\n\n")
                
                f.write("📤 Next Steps:\n")
                f.write("1. Send the detailed report file to the developer\n")
                f.write("2. Include your device model and any special features\n")
                f.write("3. Mention any functions you'd like to see added\n\n")
                
                f.write("Thank you for helping improve the MusicCast integration!\n")
            
            print(f"✅ Summary report saved: {summary_filename}")
            
            return report_filename, summary_filename
            
        except Exception as e:
            print(f"❌ Error saving files: {e}")
            return None, None
    
    def run_discovery(self):
        """Run complete discovery process."""
        self.print_header()
        
        # Get device IP
        if not self.get_device_ip():
            return False
        
        # Test connection
        if not self.test_connection():
            print("\n❌ Cannot connect to device. Please check:")
            print("• Device IP address is correct")
            print("• Device is powered on and connected to network")
            print("• Device and computer are on same network")
            print("• No firewall blocking the connection")
            return False
        
        # Store device info
        self.discovery_data["device_info"] = self.device_info
        
        # Run discovery
        print("\n🚀 Starting comprehensive API discovery...")
        print("This may take a few minutes...")
        
        self.discover_system_endpoints()
        self.discover_zone_endpoints()
        self.discover_netusb_endpoints()
        self.discover_tuner_endpoints()
        self.discover_clock_endpoints()
        self.test_special_features()
        self.analyze_capabilities()
        self.generate_summary()
        
        # Save results
        report_file, summary_file = self.save_results()
        
        if report_file and summary_file:
            print("\n🎉 Discovery completed successfully!")
            print("\n📋 Summary:")
            summary = self.discovery_data["summary"]
            print(f"• Device: {summary['device_model']} ({summary['device_id']})")
            print(f"• API endpoints found: {summary['successful_endpoints']}")
            print(f"• Zones detected: {summary['zones_detected']}")
            print(f"• Input sources: {summary['capabilities_found']}")
            
            print(f"\n📁 Files created:")
            print(f"• {report_file} (send this to developer)")
            print(f"• {summary_file} (human-readable summary)")
            
            print(f"\n📤 Next steps:")
            print(f"1. Send '{report_file}' to the developer")
            print(f"2. Include device model and any special requests")
            print(f"3. The developer will use this to enhance the integration")
            
            print(f"\nThank you for helping improve the MusicCast integration! 🙏")
            return True
        else:
            print("\n❌ Discovery completed but failed to save results")
            return False


def main():
    """Main entry point."""
    try:
        discovery = MusicCastDiscovery()
        success = discovery.run_discovery()
        
        if success:
            input("\nPress Enter to exit...")
        else:
            input("\nPress Enter to exit...")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Discovery cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please report this error to the developer")
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()