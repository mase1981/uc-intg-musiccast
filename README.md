# Yamaha MusicCast Integration for Unfolded Circle Remote 2/3

Control your Yamaha MusicCast audio devices directly from your Unfolded Circle Remote 2 or Remote 3.

![Yamaha MusicCast](https://img.shields.io/badge/Yamaha-MusicCast-red)
![Version](https://img.shields.io/badge/version-1.0.0-green)
![License](https://img.shields.io/badge/license-MPL--2.0-blue)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg)](https://paypal.me/mmiyara)

## Features

This integration provides comprehensive control of your Yamaha MusicCast audio devices directly from your Unfolded Circle Remote, supporting a wide range of audio control and streaming functions.

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

#### **Two-Entity Integration**
- **Media Player Entity**: Primary control interface with full media features
- **Remote Entity**: Button-based control for traditional remote experience
- **Synchronized State**: Both entities reflect real device status

#### **Smart State Management**
- **Playing State**: Device on and actively playing content
- **Paused State**: Device on but playback paused
- **Standby State**: Device in standby/off mode
- **Source Indication**: Current input source clearly displayed

## Supported Yamaha Models

### **Tested & Verified**
- **YAS-209** - Soundbar with wireless subwoofer (Development & Testing Platform)
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
For users running Docker environments or custom setups:

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

**Docker Run:**
```bash
docker run -d --restart=unless-stopped --net=host \
  -v $(pwd)/data:/data \
  -e UC_CONFIG_HOME=/data \
  -e UC_INTEGRATION_INTERFACE=0.0.0.0 \
  -e UC_INTEGRATION_HTTP_PORT=9090 \
  -e UC_DISABLE_MDNS_PUBLISH=false \
  --name uc-intg-yamaha-musiccast \
  ghcr.io/mase1981/uc-intg-musiccast:latest
```

### Option 3: Development Simulator
For testing without physical hardware:

**Run Simulator:**
```bash
# In separate terminal
python yamaha_simulator.py

# Simulator runs on http://localhost:8080
# Use 'localhost:8080' as device IP during setup
```

## Configuration

### Step 1: Prepare Your MusicCast Device

1. **Network Setup:**
   - Connect device to your local network (WiFi or Ethernet)
   - Note the device's IP address from your router or device display
   - Ensure device is powered on and network connected

2. **MusicCast App Verification:**
   - Download Yamaha MusicCast app to verify device connectivity
   - Confirm device appears and is controllable in the app
   - Test basic functions like play/pause and volume

3. **Network Requirements:**
   - Device and Remote must be on same local network
   - Standard HTTP port 80 communication
   - No firewall blocking required

### Step 2: Setup Integration

1. After installation, go to **Settings** → **Integrations**
2. The Yamaha MusicCast integration should appear in **Available Integrations**
3. Click **"Configure"** and follow the setup wizard:

   **Device Connection:**
   - **IP Address**: Your MusicCast device IP address (e.g., 192.168.1.100)
   - **Auto-Discovery**: Integration attempts to find devices automatically
   - **Manual Entry**: Enter IP address if auto-discovery fails

4. Click **"Test Connection"** to verify device communication
5. Integration will detect available input sources automatically
6. Click **"Complete Setup"** when connection is successful
7. Two entities will be created:
   - **[Device Name]** (Media Player)
   - **[Device Name] Remote** (Remote Control)

### Step 3: Add Entities to Activities

1. Go to **Activities** in your remote interface
2. Edit or create an activity
3. Add MusicCast entities from the **Available Entities** list:
   - **MusicCast Device** (Media Player) - Primary control interface
   - **MusicCast Device Remote** (Remote) - Button-based control
4. Configure button mappings and UI layout as desired
5. Save your activity

## Usage

### Media Player Control

Use the **MusicCast Device** media player entity:

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

Use the **MusicCast Device Remote** remote entity:

1. **Main Controls Page**:
   - Transport controls for playback management
   - Volume up/down and mute buttons
   - Power control for device on/off

2. **Sources Page**:
   - Dedicated button for each available input source
   - Quick switching between favorite sources
   - Visual confirmation of source changes

### Status Monitoring

#### **Media Player States**
- **Playing**: Device on and actively playing content with transport controls
- **Paused**: Device on but playback paused, ready to resume
- **Stopped**: Device on but no active playback
- **Standby**: Device in standby/off mode

#### **Source Information**
- Current input source always displayed
- Automatic detection of available sources
- Real-time source switching feedback

#### **Now Playing Display**
- Track title, artist, and album information
- Album artwork when available
- Playback position and total duration
- Repeat and shuffle status indicators

## Performance & Optimization

### **Intelligent Polling System**
- **Dynamic Updates**: Real-time status monitoring every 5 seconds
- **Resource Efficient**: Minimal network traffic and device load
- **Race Condition Prevention**: Advanced entity persistence management
- **Error Recovery**: Automatic reconnection after network interruptions

### **Network Requirements**
- **Local Network**: Integration requires same network as MusicCast device
- **Bandwidth**: Minimal (~500 bytes per update cycle)
- **Latency**: Optimized for typical home network performance
- **Reliability**: Graceful handling of temporary network issues

### **Entity Persistence**
- **Post-Reboot Stability**: Entities remain available after system restarts
- **State Synchronization**: Real-time sync between remote and device
- **Configuration Persistence**: Settings survive system reboots

## Troubleshooting

### Common Issues

#### **"Device Not Found"**
- Verify MusicCast device IP address is correct
- Ensure device and Remote are on same network
- Check device is powered on and network connected
- Try using MusicCast app to verify device connectivity
- Restart device and try again

#### **"Connection Failed"**
- Confirm device IP address in integration settings
- Check network connectivity between Remote and device
- Verify no firewall blocking communication
- Ensure device supports Yamaha Extended Control API
- Try connecting from MusicCast mobile app first

#### **"Sources Not Available"**
- Verify device inputs are properly connected
- Check device input configuration in Yamaha settings
- Restart integration to refresh source list
- Some sources may require content to be active

#### **"Commands Not Working"**
- Ensure device is powered on (not in deep standby)
- Verify current source supports the requested command
- Check device isn't in a restricted mode
- Try controlling device directly to confirm functionality

#### **"Integration Offline"**
- Check Remote's network connectivity
- Verify MusicCast device is still accessible
- Restart integration from Remote settings
- Check device hasn't changed IP address

### Debug Information

Enable detailed logging for troubleshooting:

**Docker Environment:**
```bash
# Add to docker-compose.yml environment section
- LOG_LEVEL=DEBUG

# View logs
docker logs uc-intg-yamaha-musiccast
```

**Integration Logs:**
- **Remote Interface**: Settings → Integrations → Yamaha MusicCast → View Logs
- **Common Errors**: Connection timeouts, API response errors, source detection issues

**Device Verification:**
- **MusicCast App**: Verify device appears and responds
- **Network Ping**: Confirm device IP is reachable
- **Browser Test**: Visit `http://device-ip/YamahaExtendedControl/v1/system/getDeviceInfo`

## Limitations

### **MusicCast API Limitations**
- **Local Network Only**: No remote/internet control of devices
- **Device Dependent**: Feature availability varies by device model
- **Source Limitations**: Some sources may not support all commands
- **Network Dependency**: Requires continuous network connectivity

### **Integration Limitations**  
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
   # Terminal 1: Start simulator
   python yamaha_simulator.py
   
   # Terminal 2: Run integration
   python uc_intg_musiccast/driver.py
   ```

4. **VS Code debugging:**
   - Open project in VS Code
   - Use F5 to start debugging session
   - Integration runs on `localhost:9090`
   - Use `localhost:8080` as device IP to connect to simulator

### Project Structure

```
uc-intg-musiccast/
├── uc_intg_musiccast/          # Main package
│   ├── __init__.py             # Package info  
│   ├── client.py               # MusicCast API client
│   ├── config.py               # Configuration management
│   ├── driver.py               # Main integration driver
│   ├── media_player.py         # Media player entity
│   └── remote.py               # Remote control entity
├── .github/workflows/          # GitHub Actions CI/CD
│   └── build.yml               # Automated build pipeline
├── .git/hooks/                 # Git hooks for quality
│   └── pre-push                # Version consistency checking
├── yamaha_simulator.py         # Development simulator
├── docker-compose.yml          # Docker deployment
├── Dockerfile                  # Container build instructions
├── docker-entry.sh             # Container entry point
├── driver.json                 # Integration metadata
├── requirements.txt            # Dependencies
├── pyproject.toml              # Python project config
└── README.md                   # This file
```

### Testing

```bash
# Install test dependencies
pip install -r requirements.txt

# Run with simulator
python yamaha_simulator.py  # Terminal 1
python uc_intg_musiccast/driver.py  # Terminal 2

# Test with real hardware
# Configure integration with actual MusicCast device IP
```

### Development Features

#### **Yamaha Simulator**
Complete MusicCast API simulator for development without hardware:
- **Full API Coverage**: All endpoints implemented
- **Realistic Responses**: Matches real device behavior
- **State Management**: Persistent state across requests
- **Debug Endpoints**: Additional debugging and reset capabilities

#### **Git Hooks**
Automated quality assurance:
- **Pre-push Hook**: Version consistency checking
- **Version Validation**: Ensures driver.json and pyproject.toml versions match
- **Tag Validation**: Verifies git tags match version numbers

#### **CI/CD Pipeline**
Automated building and deployment:
- **Multi-Architecture**: Builds for amd64 and arm64
- **Docker Images**: Automated Docker Hub publishing
- **Release Artifacts**: Automatic tar.gz generation
- **Version Management**: Semantic versioning with git tags

#### **Health Monitoring**
Production-ready health checks:
- **Health Endpoint**: `/health` endpoint for monitoring
- **Docker Health**: Integrated container health checking
- **Graceful Shutdown**: Proper cleanup on container stop

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test with simulator
4. Test with real MusicCast hardware if available
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## Advanced Features

### **Entity Persistence Management**
Advanced race condition prevention ensures entities remain available after system reboots:
- **Pre-initialization**: Entities created before UC Remote connection
- **Atomic Creation**: All entities created atomically to prevent timing issues
- **State Guards**: Protection against subscription before entity readiness

### **Source Detection**
Intelligent input source management:
- **Dynamic Discovery**: Automatic detection of available device inputs
- **Friendly Names**: Technical input IDs mapped to user-friendly names
- **Real-time Updates**: Source list updated when device configuration changes

### **State Synchronization**
Advanced state management between entities:
- **Dual Entity Support**: Media player and remote entities stay synchronized
- **Deferred Updates**: Smart update timing prevents conflicts
- **Attribute Persistence**: State maintained across connection interruptions

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
| Soundbars | YAS-209, YAS-408, SR-B20A | ✅ Tested | Full control, source switching |
| AV Receivers | RX-V6A, RX-A2A, TSR-700 | ✅ Compatible | Full control, multi-input |
| Wireless Speakers | MusicCast 20/50 | ✅ Compatible | Playback control, limited sources |
| Streaming Amps | WXA-50, R-N803D | ✅ Compatible | Full control, streaming sources |
| Piano/Keyboard | Clavinova CLP series | ✅ Compatible | Basic playback if MusicCast enabled |

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