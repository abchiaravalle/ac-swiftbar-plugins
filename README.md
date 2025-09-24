# AC SwiftBar Plugins

A collection of SwiftBar plugins for macOS menu bar functionality.

## Plugins

### 🔌 mini-tunnel.30s.py
SSH tunnel manager for ports 3845 and 12306 to mini server.
- Toggle individual tunnels on/off
- Start/stop all tunnels
- Background process management
- Real-time status with uptime

### 📡 hc911.30s.py
Hamilton County 911 calls monitor from hc911server.com API.
- Real-time 911 call updates
- Priority and status filtering
- Location mapping integration
- Cached data for performance

### ⏱️ timer.1s.py
Timer with 5-minute increments up to 1 hour.
- 5-minute increment selection
- Pause/resume functionality
- Visual countdown
- Rapid flashing when complete

### 🚀 wpengine-dynamic.30s.py
WP Engine dynamic content management.

### 🤖 chatgpt-local.30s.py (Disabled)
Local ChatGPT integration for SwiftBar - currently disabled.

### 🌐 chatgpt-webview.30s.py (Disabled)
ChatGPT webview integration for SwiftBar - currently disabled.

### 🧪 test-webview.30s.sh (Disabled)
Webview testing script for development - currently disabled.

## Installation

1. Clone this repository
2. Make scripts executable: `chmod +x *.py *.sh`
3. Copy to your SwiftBar plugins directory
4. Configure environment variables (see `.env.example`)

## Configuration

Copy `.env.example` to `.env` and configure your settings:

```bash
# SSH Configuration
SSH_USER=your_username

# HC911 API
HC911_AUTH_TOKEN=your_token
HC911_MAX_CALLS=150
```

## Requirements

- Python 3
- SwiftBar
- SSH access to configured hosts
- Internet connection for API-based plugins

## License

MIT License - feel free to use and modify as needed.
