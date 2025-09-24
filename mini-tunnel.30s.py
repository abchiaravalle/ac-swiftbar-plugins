#!/usr/bin/env python3
# <bitbar.title>Mini Tunnel</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>AC</bitbar.author>
# <bitbar.desc>Toggle SSH tunnels for ports 3845 and 12306 to mini server</bitbar.desc>
# <bitbar.dependencies>python3</bitbar.dependencies>

import os
import sys
import json
import subprocess
import signal
import time
from datetime import datetime
from pathlib import Path

# -----------------------------------
# Configuration
# -----------------------------------
CACHE_DIR = Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache")))
CACHE_FILE = CACHE_DIR / "swiftbar_mini_tunnel_cache.json"
REFRESH_INTERVAL = 30  # Refresh every 30 seconds

# SSH tunnel configuration
SSH_HOST = "mini"
SSH_USER = os.getenv("SSH_USER", os.getenv("USER", "root"))
TUNNELS = {
    "3845": {
        "remote_port": 3845,
        "local_port": 3845,
        "description": "Port 3845"
    },
    "12306": {
        "remote_port": 12306,
        "local_port": 12306,
        "description": "Port 12306"
    }
}

# -----------------------------------
# Cache Functions
# -----------------------------------
def load_tunnel_state():
    """Load tunnel state from cache"""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    
    # Default state - all tunnels stopped
    return {
        "tunnels": {
            "3845": {"running": False, "pid": None, "start_time": None},
            "12306": {"running": False, "pid": None, "start_time": None}
        },
        "last_check": None
    }

def save_tunnel_state(state):
    """Save tunnel state to cache"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception:
        pass

# -----------------------------------
# Process Management
# -----------------------------------
def is_process_running(pid):
    """Check if a process with given PID is running"""
    try:
        if pid is None:
            return False
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def kill_process(pid):
    """Kill a process by PID"""
    try:
        if pid and is_process_running(pid):
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            # Force kill if still running
            if is_process_running(pid):
                os.kill(pid, signal.SIGKILL)
            return True
    except (OSError, ProcessLookupError):
        pass
    return False

def start_ssh_tunnel(port):
    """Start SSH tunnel for the specified port"""
    if port not in TUNNELS:
        return False, "Invalid port"
    
    tunnel_config = TUNNELS[port]
    
    # Check if tunnel is already running
    if check_tunnel_status(port):
        return False, "Tunnel already running"
    
    # SSH command: ssh -R remote_port:127.0.0.1:local_port user@host
    cmd = [
        "ssh", 
        "-R", f"{tunnel_config['remote_port']}:127.0.0.1:{tunnel_config['local_port']}",
        "-N",  # Don't execute remote commands
        "-f",  # Run in background
        "-o", "ConnectTimeout=10",  # Add timeout
        "-o", "ServerAliveInterval=60",  # Keep connection alive
        "-o", "ServerAliveCountMax=3",  # Max missed keepalives
        f"{SSH_USER}@{SSH_HOST}"
    ]
    
    try:
        # Start the SSH tunnel in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,  # Capture stderr for debugging
            preexec_fn=os.setsid  # Create new process group
        )
        
        # Give it a moment to establish
        time.sleep(3)
        
        # Check if it's still running
        if process.poll() is None:
            return True, process.pid
        else:
            # SSH with -f forks, so the parent process exits immediately
            # Check if there's actually a tunnel process running
            actual_pid = find_ssh_tunnel_process(port)
            if actual_pid:
                return True, actual_pid
            else:
                # Get error output for debugging
                stderr_output = process.stderr.read().decode() if process.stderr else "No error output"
                return False, f"SSH tunnel failed to start: {stderr_output}"
            
    except Exception as e:
        return False, f"Error starting tunnel: {str(e)}"

def stop_ssh_tunnel(port):
    """Stop SSH tunnel for the specified port"""
    state = load_tunnel_state()
    
    if port not in state["tunnels"]:
        return False, "Port not found in state"
    
    tunnel_state = state["tunnels"][port]
    stopped_any = False
    
    # Kill the process we know about
    if tunnel_state["running"] and tunnel_state["pid"]:
        if kill_process(tunnel_state["pid"]):
            stopped_any = True
    
    # Also kill any other SSH tunnel processes for this port
    try:
        result = subprocess.run(
            ["pkill", "-f", f"ssh.*-R {port}:127.0.0.1:{port}.*{SSH_HOST}"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            stopped_any = True
    except Exception:
        pass
    
    # Update state
    state["tunnels"][port]["running"] = False
    state["tunnels"][port]["pid"] = None
    state["tunnels"][port]["start_time"] = None
    save_tunnel_state(state)
    
    if stopped_any:
        return True, "Tunnel stopped"
    else:
        return True, "No tunnel was running"

def find_ssh_tunnel_process(port):
    """Find SSH tunnel process for the specified port"""
    try:
        # Look for SSH processes with the specific tunnel pattern
        result = subprocess.run(
            ["pgrep", "-f", f"ssh.*-R {port}:127.0.0.1:{port}.*{SSH_HOST}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip()]
            return pids[0] if pids else None
    except Exception:
        pass
    return None

def check_tunnel_status(port):
    """Check if tunnel is actually running and update state"""
    state = load_tunnel_state()
    
    if port not in state["tunnels"]:
        return False
    
    tunnel_state = state["tunnels"][port]
    
    # First check if we have a PID in our state
    if tunnel_state["running"] and tunnel_state["pid"]:
        if is_process_running(tunnel_state["pid"]):
            return True
        else:
            # Process died, update state
            state["tunnels"][port]["running"] = False
            state["tunnels"][port]["pid"] = None
            state["tunnels"][port]["start_time"] = None
            save_tunnel_state(state)
    
    # If not in our state, check if there's actually a running tunnel
    actual_pid = find_ssh_tunnel_process(port)
    if actual_pid:
        # Update our state with the actual running process
        state["tunnels"][port]["running"] = True
        state["tunnels"][port]["pid"] = actual_pid
        if not state["tunnels"][port]["start_time"]:
            state["tunnels"][port]["start_time"] = datetime.now().isoformat()
        save_tunnel_state(state)
        return True
    
    return False

def get_tunnel_uptime(port):
    """Get tunnel uptime in minutes"""
    state = load_tunnel_state()
    
    if port not in state["tunnels"]:
        return 0
    
    tunnel_state = state["tunnels"][port]
    
    if not tunnel_state["running"] or not tunnel_state["start_time"]:
        return 0
    
    try:
        start_time = datetime.fromisoformat(tunnel_state["start_time"])
        uptime = datetime.now() - start_time
        return int(uptime.total_seconds() / 60)
    except:
        return 0

# -----------------------------------
# Menu Rendering
# -----------------------------------
def render_menu():
    """Render the SwiftBar menu"""
    state = load_tunnel_state()
    
    # Check tunnel statuses
    running_tunnels = 0
    for port in TUNNELS.keys():
        is_running = check_tunnel_status(port)
        if is_running:
            running_tunnels += 1
    
    # Main menu bar display
    if running_tunnels == 0:
        print("🔌 Mini Tunnel")
    elif running_tunnels == len(TUNNELS):
        print("🔌 Mini Tunnel ✅")
    else:
        print(f"🔌 Mini Tunnel ({running_tunnels}/{len(TUNNELS)})")
    
    print("---")
    
    # Tunnel controls for each port
    for port, config in TUNNELS.items():
        tunnel_state = state["tunnels"][port]
        is_running = check_tunnel_status(port)
        
        if is_running:
            uptime = get_tunnel_uptime(port)
            uptime_str = f" ({uptime}m)" if uptime > 0 else ""
            print(f"🟢 {config['description']}{uptime_str}")
            print(f"--Stop Tunnel | bash={sys.argv[0]} param1=stop param2={port} terminal=false refresh=true")
        else:
            print(f"🔴 {config['description']}")
            print(f"--Start Tunnel | bash={sys.argv[0]} param1=start param2={port} terminal=false refresh=true")
        
        print(f"--Status: {'Running' if is_running else 'Stopped'}")
        if is_running and tunnel_state.get("pid"):
            print(f"--PID: {tunnel_state['pid']}")
        print("---")
    
    # Global controls
    if running_tunnels > 0:
        print(f"Stop All Tunnels | bash={sys.argv[0]} param1=stop_all terminal=false refresh=true")
        print("---")
    
    if running_tunnels < len(TUNNELS):
        print(f"Start All Tunnels | bash={sys.argv[0]} param1=start_all terminal=false refresh=true")
        print("---")
    
    # Connection info
    print(f"SSH Host: {SSH_USER}@{SSH_HOST}")
    print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# -----------------------------------
# Action Handlers
# -----------------------------------
def handle_start_tunnel(port):
    """Handle starting a tunnel"""
    if port not in TUNNELS:
        print(f"❌ Invalid port: {port}")
        return
    
    # Check if already running
    if check_tunnel_status(port):
        print(f"✅ Tunnel for port {port} is already running")
        return
    
    success, result = start_ssh_tunnel(port)
    
    if success:
        # Update state
        state = load_tunnel_state()
        state["tunnels"][port]["running"] = True
        state["tunnels"][port]["pid"] = result
        state["tunnels"][port]["start_time"] = datetime.now().isoformat()
        save_tunnel_state(state)
        print(f"✅ Started tunnel for port {port} (PID: {result})")
    else:
        print(f"❌ Failed to start tunnel for port {port}: {result}")

def handle_stop_tunnel(port):
    """Handle stopping a tunnel"""
    if port not in TUNNELS:
        print(f"❌ Invalid port: {port}")
        return
    
    success, result = stop_ssh_tunnel(port)
    
    if success:
        print(f"✅ Stopped tunnel for port {port}")
    else:
        print(f"❌ Failed to stop tunnel for port {port}: {result}")

def handle_start_all_tunnels():
    """Handle starting all tunnels"""
    results = []
    for port in TUNNELS.keys():
        if not check_tunnel_status(port):
            success, result = start_ssh_tunnel(port)
            if success:
                # Update state
                state = load_tunnel_state()
                state["tunnels"][port]["running"] = True
                state["tunnels"][port]["pid"] = result
                state["tunnels"][port]["start_time"] = datetime.now().isoformat()
                save_tunnel_state(state)
                results.append(f"✅ Port {port}")
            else:
                results.append(f"❌ Port {port}: {result}")
        else:
            results.append(f"⏭️ Port {port} (already running)")
    
    for result in results:
        print(result)

def handle_stop_all_tunnels():
    """Handle stopping all tunnels"""
    results = []
    for port in TUNNELS.keys():
        if check_tunnel_status(port):
            success, result = stop_ssh_tunnel(port)
            if success:
                results.append(f"✅ Port {port}")
            else:
                results.append(f"❌ Port {port}: {result}")
        else:
            results.append(f"⏭️ Port {port} (not running)")
    
    for result in results:
        print(result)

# -----------------------------------
# Main Execution
# -----------------------------------
if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "start" and len(sys.argv) > 2:
            handle_start_tunnel(sys.argv[2])
        elif command == "stop" and len(sys.argv) > 2:
            handle_stop_tunnel(sys.argv[2])
        elif command == "start_all":
            handle_start_all_tunnels()
        elif command == "stop_all":
            handle_stop_all_tunnels()
        else:
            print("❌ Invalid command")
    else:
        # Render the menu
        render_menu()
