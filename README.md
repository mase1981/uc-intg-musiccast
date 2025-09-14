# Yamaha MusicCast Integration for Unfolded Circle Remote 2/3

Control your Yamaha MusicCast audio devices directly from your Unfolded Circle Remote 2 or Remote 3. **Now supports multiple devices!**

![Yamaha MusicCast](https://img.shields.io/badge/Yamaha-MusicCast-red)
![Version](https://img.shields.io/badge/version-1.0.0-green)
![License](https://img.shields.io/badge/license-MPL--2.0-blue)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg)](https://paypal.me/mmiyara)

## Features

This integration provides comprehensive control of your Yamaha MusicCast audio devices directly from your Unfolded Circle Remote, supporting a wide range of audio control and streaming functions. **Multi-device support** allows you to control up to 10 MusicCast devices from a single integration.

### 🎵 **Media Player Control**

Transform your remote into a powerful MusicCast controller with full playback management:

#### **Playback Control**
- **Play/Pause** - Seamless playback control with visual feedback
- **Stop** - Stop current playback and clear now playing
- **Previous/Next Track** - Navigate through your music collection
- **Volume Control** - Precise volume adjustment with step controls
- **Mute Toggle** - Quick mute/unmute functionality

#### **Audio Source Management**
- **Source Switching** - Easy switching between HDMI, Bluetooth, Spotify, and Analog inputs
- **Input Selection** - Direct source selection through media player interface
- **Real-time Source Display** - Current input always visible on remote

#### **Advanced Features**
- **Repeat Control** - Off, One, All repeat modes
- **Shuffle Control** - Toggle shuffle on/off
- **Now Playing Display** - Artist, album, track, and artwork display
- **Playback Position** - Real-time position tracking with duration
- **Multi-Device Support** - Control multiple MusicCast devices independently

### 🎮 **Remote Control Interface**

Comprehensive MusicCast device control through dedicated remote entity:

#### **Main Controls Page**
- **Transport Controls** - Play/Pause, Previous, Next, Stop
- **Volume Management** - Volume Up/Down, Mute toggle
- **Power Control** - Device power on/off/toggle

#### **Sources Page**
- **Input Selection** - Dedicated buttons for each available input
- **Quick Switching** - Single-button access to favorite sources
- **Visual Feedback** - Source status reflected in real-time

### 📊 **Visual Status Display**

#### **Dynamic Status Information**
Real-time display of device and playback status:
- **Device State**: Power on/off, standby status
- **Playback State**: Playing, paused, stopped with visual indicators
- **Current Track**: Title, artist, album information
- **Album Artwork**: High-quality cover art display

#### **Multi-Entity Integration**
- **Media Player Entity**: Primary control interface with full media features (one per device)
- **Remote Entity**: Button-based control for traditional remote experience (one per device)
- **Synchronized State**: All entities reflect real device status
- **Independent Control**: Each device operates independently

#### **Smart State Management**
- **Playing State**: Device on and actively playing content
- **Paused State**: Device on but playback paused
- **Standby State**: Device in standby/off mode
- **Source Indication**: Current input source clearly displayed

## Multi-Device Support

### **Setup Multiple Devices**
The integration now supports **1-10 MusicCast devices** in a single setup:

1. **Device Count Selection**: Choose how many devices to configure during setup
2. **Individual Configuration**: Enter IP address and name for each device
3. **Concurrent Testing**: All devices tested simultaneously during setup
4. **Independent Entities**: Each device gets its own media player and remote entities

### **Entity Naming**
Each device creates two entities:
- **Media Player**: `Device Name` (e.g., "Living Room YAS-209")
- **Remote Control**: `Device Name Remote` (e.g., "Living Room YAS-209 Remote")

### **Benefits**
- **Centralized Control**: Manage all MusicCast devices from one integration
- **Room-Based Setup**: Perfect for multi-room audio systems
- **Individual Control**: Each device operates independently
- **Simplified Management**: Single integration for your entire MusicCast ecosystem

## Supported Yamaha Models

### **Tested & Verified**
- **YAS-209** - Soundbar with wireless subwoofer (Development & Testing Platform)
- **RX-A8A** - AVENTAGE 11.2-channel AV receiver (Real device testing)
- **SR-B20A** - Compact soundbar with Alexa
- **YAS-408** - Front surround soundbar

### **Expected Compatibility**
This integration should work with **any Yamaha device supporting MusicCast**, including:
- **Soundbars** - YAS series, SR series, YSP series
- **AV Receivers** - RX-V series, RX-A series, AVENTAGE series
- **Wireless Speakers** - MusicCast 20, MusicCast 50, etc.
- **Streaming Amplifiers** - WXA-50, WXC-50, R-N803D
- **Piano/Keyboard** - Clavinova, P-series with MusicCast

### **Requirements**
- **MusicCast Support** - Device must support Yamaha MusicCast
- **Network Connection** - Wired or wireless network connectivity
- **Yamaha Extended Control API** - Built into all MusicCast devices
- **Local Network Access** - Integration requires same network as device

## Installation

### Option 1: Remote Web Interface (Recommended)
1. Navigate to the [**Releases**](https://github.com/mase1981/uc-intg-musiccast/releases) page
2. Download the latest `uc-intg-yamaha-musiccast-<version>.tar.gz` file
3. Open your remote's web interface (`http://your-remote-ip`)
4. Go to **Settings** → **Integrations** → **Add Integration**
5. Click **Upload** and select the downloaded `.tar.gz` file

### Option 2: Docker (Advanced Users)

The integration is available as a pre-built Docker image from GitHub Container Registry:

**Image**: `ghcr.io/mase1981/uc-intg-musiccast:latest`

**Docker Compose:**
```yaml
version: '3.8'

services:
  yamaha-musiccast-integration:
    image: ghcr.io/mase1981/uc-intg-musiccast:latest
    container_name: uc-intg-yamaha-musiccast
    restart: unless-stopped
    network_mode: host  # Required for device discovery
    volumes:
      - ./data:/data  # Persistent configuration storage
    environment:
      - UC_CONFIG_HOME=/data
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_DISABLE_MDNS_PUBLISH=false
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    labels:
      - "com.unfoldedcircle.integration=yamaha-musiccast"
      - "com.unfoldedcircle.version=1.0.0"
```

### Option 3: Development Simulator
For testing without physical hardware, including multi-device testing:

**Single Device:**
```bash
python yamaha_simulator.py --single --port 8080
# Use 'localhost:8080' as device IP during setup
```

**Multi-Device Testing:**
```bash
python yamaha_simulator.py --count 3
# Creates 3 simulated devices on ports 8080, 8081, 8082
# Use 'localhost:8080', 'localhost:8081', 'localhost:8082' during setup
```

## Configuration

### Step 1: Prepare Your MusicCast Device(s)

1. **Network Setup:**
   - Connect each device to your local network (WiFi or Ethernet)
   - Note each device's IP address from your router or device display
   - Ensure all devices are powered on and network connected

2. **MusicCast App Verification:**
   - Download Yamaha MusicCast app to verify device connectivity
   - Confirm each device appears and is controllable in the app
   - Test basic functions like play/pause and volume

3. **Network Requirements:**
   - All devices and Remote must be on same local network
   - Standard HTTP port 80 communication
   - No firewall blocking required

### Step 2: Setup Integration

1. After installation, go to **Settings** → **Integrations**
2. The Yamaha MusicCast integration should appear in **Available Integrations**
3. Click **"Configure"** and follow the setup wizard:

#### **Single Device Setup**
   - **Number of Devices**: Select "1"
   - **IP Address**: Enter device IP (e.g., 192.168.1.100)
   - **Test Connection**: Verify device communication
   - **Complete Setup**: Creates 2 entities (Media Player + Remote)

#### **Multi-Device Setup**
   - **Number of Devices**: Select 2-10 devices
   - **Device Configuration**: For each device, enter:
     - **IP Address**: Device IP address
     - **Device Name**: Friendly name (e.g., "Living Room YAS-209")
   - **Concurrent Testing**: All devices tested simultaneously
   - **Complete Setup**: Creates 2 entities per device

4. Integration will detect available input sources automatically for each device
5. Entities will be created and available immediately

### Step 3: Add Entities to Activities

1. Go to **Activities** in your remote interface
2. Edit or create an activity
3. Add MusicCast entities from the **Available Entities** list:
   - **Device Name** (Media Player) - Primary control interface
   - **Device Name Remote** (Remote) - Button-based control
4. Configure button mappings and UI layout as desired
5. Save your activity

## Usage

### Media Player Control

Use the **MusicCast Device** media player entity for each device:

1. **Playback Control**:
   - **Play/Pause**: Toggle playback state
   - **Stop**: Stop playback and clear now playing
   - **Previous/Next**: Navigate tracks in current playlist/source

2. **Volume Control**:
   - **Volume Slider**: Precise volume adjustment
   - **Volume +/-**: Step volume control
   - **Mute Toggle**: Quick mute/unmute

3. **Source Selection**:
   - Click **Sources** button to view available inputs
   - Select from HDMI, Bluetooth, Spotify, Analog, etc.
   - Current source displayed in media player

4. **Advanced Features**:
   - **Repeat**: Cycle through Off/One/All modes
   - **Shuffle**: Toggle shuffle on/off
   - **Now Playing**: View current track, artist, album, artwork

### Remote Control

Use the **MusicCast Device Remote** remote entity for traditional control:

1. **Main Controls Page**:
   - Transport controls for playback management
   - Volume up/down and mute buttons
   - Power control for device on/off

2. **Sources Page**:
   - Dedicated button for each available input source
   - Quick switching between favorite sources
   - Visual confirmation of source changes

### Multi-Device Management

When using multiple devices:

1. **Independent Control**: Each device operates completely independently
2. **Room-Based Activities**: Create activities for each room/device
3. **Centralized Overview**: All devices visible in integration settings
4. **Synchronized Status**: Real-time status updates for all devices

## Performance & Optimization

### **Intelligent Polling System**
- **Dynamic Updates**: Real-time status monitoring every 5 seconds per device
- **Resource Efficient**: Minimal network traffic and device load
- **Multi-Device Optimization**: Concurrent status updates for all devices
- **Error Recovery**: Automatic reconnection after network interruptions

### **Network Requirements**
- **Local Network**: Integration requires same network as MusicCast devices
- **Bandwidth**: Minimal (~500 bytes per device per update cycle)
- **Latency**: Optimized for typical home network performance
- **Reliability**: Graceful handling of temporary network issues

### **Entity Persistence**
- **Post-Reboot Stability**: All entities remain available after system restarts
- **State Synchronization**: Real-time sync between remote and devices
- **Configuration Persistence**: Settings survive system reboots

## Troubleshooting

### Common Issues

#### **"Device Not Found" (Multi-Device)**
- Verify all device IP addresses are correct
- Ensure all devices and Remote are on same network
- Check each device is powered on and network connected
- Try using MusicCast app to verify each device connectivity
- Verify devices don't conflict on same IP address

#### **"Partial Device Setup"**
- Some devices may connect while others fail
- Check failed device IP addresses and network connectivity
- Successfully connected devices will still work
- Re-run setup to add failed devices

#### **"Commands Not Working"**
- Ensure device is powered on (not in deep standby)
- Verify current source supports the requested command
- Check device isn't in a restricted mode
- Try controlling device directly to confirm functionality

#### **"Integration Offline"**
- Check Remote's network connectivity
- Verify each MusicCast device is still accessible
- Restart integration from Remote settings
- Check devices haven't changed IP addresses

### Debug Information

Enable detailed logging for troubleshooting:

**Docker Environment:**
```bash
# Add to docker-compose.yml environment section
- LOG_LEVEL=DEBUG

# View logs
docker logs uc-intg-yamaha-musiccast
```

**Multi-Device Verification:**
- **MusicCast App**: Verify each device appears and responds
- **Network Ping**: Confirm each device IP is reachable
- **Browser Test**: Visit `http://device-ip/YamahaExtendedControl/v1/system/getDeviceInfo` for each device

## Limitations

### **MusicCast API Limitations**
- **Local Network Only**: No remote/internet control of devices
- **Device Dependent**: Feature availability varies by device model
- **Source Limitations**: Some sources may not support all commands
- **Network Dependency**: Requires continuous network connectivity

### **Integration Limitations**  
- **Maximum Devices**: Up to 10 devices per integration instance
- **Single Zone**: Currently supports main zone only
- **No Multi-Room**: Multi-room/zone linking not implemented
- **Limited Preset Support**: Preset management not yet implemented
- **No EQ Control**: Equalizer settings not accessible

### **Compatibility Notes**
- **Newer Models**: Latest MusicCast devices fully supported
- **Older Models**: Basic functionality on older devices
- **Firmware Updates**: Keep device firmware updated for best compatibility

## For Developers

### Local Development

1. **Clone and setup:**
   ```bash
   git clone https://github.com/mase1981/uc-intg-musiccast.git
   cd uc-intg-musiccast
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configuration:**
   Integration uses environment variables and config files:
   ```bash
   export UC_CONFIG_HOME=./config
   # Config automatically created during setup
   ```

3. **Run development simulator:**
   ```bash
   # Terminal 1: Start multi-device simulator
   python yamaha_simulator.py --count 3
   
   # Terminal 2: Run integration
   python uc_intg_musiccast/driver.py
   ```

4. **VS Code debugging:**
   - Open project in VS Code
   - Use F5 to start debugging session
   - Integration runs on `localhost:9090`
   - Use simulator addresses for device IPs

### Testing Multi-Device Setup

```bash
# Test with 3 simulated devices
python yamaha_simulator.py --count 3

# In integration setup:
# Device count: 3
# Device 1: localhost:8080 (name: Living Room YAS-209)
# Device 2: localhost:8081 (name: Kitchen SR-B20A) 
# Device 3: localhost:8082 (name: Bedroom MusicCast 20)
```

### Project Structure

```
uc-intg-musiccast/
├── uc_intg_musiccast/          # Main package
│   ├── __init__.py             # Package info  
│   ├── client.py               # MusicCast API client
│   ├── config.py               # Configuration management (enhanced)
│   ├── driver.py               # Main integration driver (multi-device)
│   ├── media_player.py         # Media player entity (enhanced)
│   └── remote.py               # Remote control entity (enhanced)
├── .github/workflows/          # GitHub Actions CI/CD
│   └── build.yml               # Automated build pipeline
├── yamaha_simulator.py         # Multi-device development simulator
├── docker-compose.yml          # Docker deployment
├── Dockerfile                  # Container build instructions
├── docker-entry.sh             # Container entry point
├── driver.json                 # Integration metadata (enhanced)
├── requirements.txt            # Dependencies
├── pyproject.toml              # Python project config
└── README.md                   # This file
```

### Development Features

#### **Multi-Device Yamaha Simulator**
Complete MusicCast API simulator for development without hardware:
- **Multiple Device Support**: Simulate 1-10 devices simultaneously
- **Full API Coverage**: All endpoints implemented
- **Realistic Responses**: Matches real device behavior
- **Unique Device States**: Each simulated device has different content
- **Concurrent Testing**: Perfect for multi-device development

#### **CI/CD Pipeline**
Automated building and deployment:
- **Multi-Architecture**: Builds for amd64 and arm64
- **Docker Images**: Automated GitHub Container Registry publishing
- **Release Artifacts**: Automatic tar.gz generation
- **Version Management**: Semantic versioning with git tags

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test with multi-device simulator
4. Test with real MusicCast hardware if available
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## Advanced Features

### **Entity Persistence Management**
Advanced race condition prevention ensures entities remain available after system reboots:
- **Pre-initialization**: Entities created before UC Remote connection
- **Atomic Creation**: All entities created atomically to prevent timing issues
- **Multi-Device Coordination**: Proper entity management across multiple devices

### **Dynamic Source Detection**
Intelligent input source management:
- **Device-Specific Sources**: Automatic detection based on device capabilities
- **Per-Device Configuration**: Each device maintains its own source list
- **Real-time Updates**: Source list updated when device configuration changes

### **State Synchronization**
Advanced state management between entities:
- **Dual Entity Support**: Media player and remote entities stay synchronized per device
- **Deferred Updates**: Smart update timing prevents conflicts
- **Multi-Device Independence**: Each device operates independently

## Security Considerations

### **Network Security**
- **Local Network Only**: Communication limited to local network
- **No Authentication**: MusicCast devices typically don't require authentication
- **HTTP Protocol**: Standard HTTP communication (no HTTPS required)

### **Privacy**
- **No Data Collection**: Integration doesn't collect or transmit personal data
- **Local Processing**: All processing happens locally on Remote device
- **No Cloud Dependency**: No external services or cloud connectivity required

## Compatibility Matrix

| Device Type | Example Models | Status | Features |
|-------------|----------------|---------|-----------|
| Soundbars | YAS-209, YAS-408, SR-B20A | ✅ Tested | Full control, source switching, multi-device |
| AV Receivers | RX-V6A, RX-A8A, TSR-700 | ✅ Tested | Full control, multi-input, sound programs, multi-device |
| Wireless Speakers | MusicCast 20/50 | ✅ Compatible | Playback control, limited sources, multi-device |
| Streaming Amps | WXA-50, R-N803D | ✅ Compatible | Full control, streaming sources, multi-device |
| Piano/Keyboard | Clavinova CLP series | ✅ Compatible | Basic playback if MusicCast enabled, multi-device |

## License

This project is licensed under the Mozilla Public License 2.0 - see the [LICENSE](LICENSE) file for details.

## Credits

- **Developer**: Meir Miyara
- **Yamaha MusicCast**: Yamaha Extended Control API
- **Unfolded Circle**: Remote 2/3 integration framework (ucapi)
- **Community**: Testing and feedback from UC community

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-musiccast/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)

---

**Made with ❤️ for the Unfolded Circle Community** 

**Thank You**: Meir Miyara