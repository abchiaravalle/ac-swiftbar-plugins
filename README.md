# AC SwiftBar Plugins

A collection of SwiftBar plugins for macOS menu bar functionality.

## Active Plugins

### 🔌 mini-tunnel.30s.py
**SSH Tunnel Manager for Ports 3845 and 12306**

A comprehensive SSH tunnel management system that creates and maintains reverse SSH tunnels to a "mini" server. The plugin automatically detects existing tunnels, manages background processes, and provides real-time status monitoring.

**How it works:**
- **SSH Command Generation**: Creates SSH commands with reverse port forwarding (`ssh -R remote_port:127.0.0.1:local_port`)
- **Process Management**: Uses `subprocess.Popen` with process groups to manage background SSH processes
- **Process Detection**: Uses `pgrep` to find existing tunnel processes and syncs internal state
- **Connection Monitoring**: Implements SSH keepalive options (`ServerAliveInterval=60`, `ServerAliveCountMax=3`)
- **State Persistence**: Caches tunnel state (PID, start time, running status) in JSON format
- **Automatic Cleanup**: Uses `pkill` to clean up orphaned or duplicate tunnel processes

**Features:**
- Individual tunnel control for ports 3845 and 12306
- Bulk start/stop all tunnels functionality
- Real-time uptime tracking in minutes
- Process ID monitoring and display
- Automatic detection of manually started tunnels
- Background process management with proper cleanup

**Menu Interface:**
- Main bar shows tunnel count (e.g., "🔌 Mini Tunnel (1/2)" or "🔌 Mini Tunnel ✅")
- Green indicators for running tunnels with uptime
- Red indicators for stopped tunnels
- Individual start/stop controls for each port
- Global start all/stop all options

### 📡 hc911.30s.py
**Hamilton County 911 Emergency Calls Monitor**

A real-time emergency services monitoring system that fetches active 911 calls from the Hamilton County API and displays them in an organized, color-coded interface with mapping integration.

**How it works:**
- **API Integration**: Connects to `https://hc911server.com/api/calls` with authentication headers
- **Data Caching**: Implements 25-second cache to reduce API load (refreshes every 30s)
- **Fallback System**: Uses stale cache data if API fails to maintain continuity
- **Data Processing**: Parses JSON response and categorizes calls by priority, status, and agency
- **Location Services**: Generates Apple Maps links from latitude/longitude coordinates
- **Smart Filtering**: Limits display to 150 calls maximum to prevent menu overflow

**Data Structure:**
- **Priority Levels**: PRI 1 (🚨), PRI 2 (⚠️), PRI 3 (🔵), PRI 4 (⚪)
- **Status Types**: Queued (🟡), Enroute (🟠), On Scene (🔴), At Hospital (🏥), Stacked (📚), Transporting (🚑)
- **Agency Types**: EMS (🚑), Fire (🚒), Law (👮), HC911 (📡)

**Menu Interface:**
- Main bar shows recent call count (e.g., "hc911 3" for 3 calls in last 10 minutes)
- Summary section with total calls, priority counts, and status breakdowns
- Top 5 most recent calls displayed with full details
- Calls grouped by priority with status-based sub-grouping
- Direct Apple Maps integration for location viewing
- Real-time timestamp display

**Configuration:**
- `HC911_AUTH_TOKEN`: API authentication token
- `HC911_MAX_CALLS`: Maximum calls to display (default: 150)

### ⏱️ timer.1s.py
**Precision Timer with 5-Minute Increments**

A sophisticated timer system that provides precise timing with pause/resume functionality, visual countdown, and attention-grabbing completion alerts.

**How it works:**
- **State Management**: Maintains 5 timer states (STOPPED, RUNNING, PAUSED, COMPLETED, FLASHING)
- **Precision Timing**: 1-second refresh rate for accurate countdown display
- **Pause Logic**: Tracks total paused duration and adjusts end time accordingly
- **Completion Alert**: Rapid flashing every 0.5 seconds when timer completes
- **Persistent State**: Saves timer state to JSON cache for persistence across SwiftBar restarts

**Timer States:**
- **STOPPED**: No active timer, shows duration selection menu
- **RUNNING**: Active countdown with real-time display
- **PAUSED**: Timer suspended, shows remaining time
- **COMPLETED**: Timer finished, shows completion message
- **FLASHING**: Alternating display for attention-grabbing completion alert

**Features:**
- 5-minute increment selection (5, 10, 15... up to 60 minutes)
- Pause and resume functionality with accurate time tracking
- Visual countdown in MM:SS format
- Rapid flashing completion alert
- Dismiss functionality to clear completed timers
- State persistence across system restarts

**Menu Interface:**
- Main bar shows current timer state and remaining time
- Duration selection menu when stopped
- Pause/resume/stop controls when running
- Dismiss option when completed
- Real-time countdown display

### 🚀 wpengine-dynamic.30s.py
**WP Engine Multi-Account Management System**

A comprehensive WordPress hosting management tool that interfaces with the WP Engine API to provide install management, SSH access, and safe administrative actions across multiple accounts.

**How it works:**
- **Multi-Account Support**: Manages up to 5 WP Engine accounts simultaneously
- **API Integration**: Uses WP Engine REST API v1 for install management
- **Environment Loading**: Automatically loads configuration from `.env` file
- **Caching System**: 5-minute cache to reduce API calls and improve performance
- **SSH Integration**: Generates SSH commands for direct server access
- **Safe Actions Only**: Implements GET and POST operations only (no PATCH/DELETE)

**Core Functionality:**
- **Install Discovery**: Fetches all WordPress installations across configured accounts
- **SSH Access**: Direct terminal/iTerm2 integration with proper SSH key handling
- **Cache Management**: Purge CDN cache for individual installs
- **Backup Operations**: Request backups and monitor backup status
- **Domain Management**: List and manage custom domains
- **Install Details**: View comprehensive installation information

**API Operations:**
- **GET Operations**: Fetch installs, domains, backup status, install details
- **POST Operations**: Request backups, purge cache
- **SSH Commands**: Terminal/iTerm2 integration with environment-specific commands

**Menu Interface:**
- Main bar shows total install count (e.g., "WPE 25")
- Alphabetically sorted install list with name and slug
- Per-install actions: SSH access, cache purge, backup operations
- Account-specific organization
- MainWP integration if configured

**Configuration Variables:**
- `WPE_API_USER1-5`: WP Engine API usernames for up to 5 accounts
- `WPE_API_PASS1-5`: Corresponding API passwords
- `WPE_SSH_KEY`: SSH private key path for server access
- `WPE_MAX_INSTALLS`: Maximum installs to display (default: 100)
- `REFRESH_SECS`: Cache refresh interval (default: 300 seconds)

## Disabled Plugins

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
