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
SSH_USER = os.getenv("SSH_USER", os.getenv("USER", "root"))

# Available SSH hosts
SSH_HOSTS = {
    "mini": {"hostname": "mini", "display": "Mini"},
    "pipex": {"hostname": "pipex", "display": "Pipex"}
}

# Permanent ports to tunnel (without host assignment - selected dynamically)
PERMANENT_PORTS = ["3845", "12306", "54106", "60351", "57682"]

# -----------------------------------
# Cache Functions
# -----------------------------------
def load_tunnel_state():
    """Load tunnel state from cache"""
    default_state = {
        "tunnels": {},
        "last_check": None,
        "temporary_ports": []  # Track temporary ports added by user
    }

    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                state = json.load(f)

                # Ensure temporary_ports exists
                if "temporary_ports" not in state:
                    state["temporary_ports"] = []

                return state
    except Exception:
        pass

    return default_state

def save_tunnel_state(state):
    """Save tunnel state to cache"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception:
        pass

def get_all_ports(state):
    """Get all ports (permanent + temporary from state)"""
    all_ports = set(PERMANENT_PORTS)

    # Add any temporary ports that are in the state
    if state and "temporary_ports" in state:
        all_ports.update(state["temporary_ports"])

    return sorted(all_ports)

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

def start_ssh_tunnel(port, host_key, direction="remote"):
    """Start SSH tunnel for the specified port to the specified host

    Args:
        port: The port number to tunnel
        host_key: The SSH host key (mini, pipex, etc.)
        direction: "remote" for -R (expose local port on remote), "local" for -L (access remote port locally)
    """
    if host_key not in SSH_HOSTS:
        return False, "Invalid host"

    tunnel_key = f"{port}:{direction}@{host_key}"
    ssh_host = SSH_HOSTS[host_key]["hostname"]

    # Check if tunnel is already running
    if check_tunnel_status(port, host_key, direction):
        return False, "Tunnel already running"

    # Just use hostname, let SSH config determine the user
    ssh_target = ssh_host

    # SSH command varies based on direction
    if direction == "remote":
        # -R: Expose local port on remote host (remote can access localhost:port)
        tunnel_arg = f"{port}:127.0.0.1:{port}"
        tunnel_flag = "-R"
    else:  # local
        # -L: Access remote port locally (localhost:port accesses remote:port)
        tunnel_arg = f"{port}:127.0.0.1:{port}"
        tunnel_flag = "-L"

    cmd = [
        "ssh",
        tunnel_flag, tunnel_arg,
        "-N",  # Don't execute remote commands
        "-f",  # Run in background
        "-o", "ConnectTimeout=10",  # Add timeout
        "-o", "ServerAliveInterval=60",  # Keep connection alive
        "-o", "ServerAliveCountMax=3",  # Max missed keepalives
        ssh_target
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
            actual_pid = find_ssh_tunnel_process(port, host_key, direction)
            if actual_pid:
                return True, actual_pid
            else:
                # Get error output for debugging
                stderr_output = process.stderr.read().decode() if process.stderr else "No error output"
                return False, f"SSH tunnel failed to start: {stderr_output}"

    except Exception as e:
        return False, f"Error starting tunnel: {str(e)}"

def stop_ssh_tunnel(port, host_key, direction="remote"):
    """Stop SSH tunnel for the specified port, host, and direction"""
    state = load_tunnel_state()

    tunnel_key = f"{port}:{direction}@{host_key}"
    if tunnel_key not in state["tunnels"]:
        return False, "Tunnel not found in state"

    tunnel_state = state["tunnels"][tunnel_key]
    ssh_host = SSH_HOSTS[host_key]["hostname"]
    stopped_any = False

    # Kill the process we know about
    if tunnel_state["running"] and tunnel_state["pid"]:
        if kill_process(tunnel_state["pid"]):
            stopped_any = True

    # Also kill any other SSH tunnel processes for this port
    try:
        tunnel_flag = "-R" if direction == "remote" else "-L"
        result = subprocess.run(
            ["pkill", "-f", f"ssh.*{tunnel_flag} {port}:127.0.0.1:{port}.*{ssh_host}"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            stopped_any = True
    except Exception:
        pass

    # Update state
    state["tunnels"][tunnel_key]["running"] = False
    state["tunnels"][tunnel_key]["pid"] = None
    state["tunnels"][tunnel_key]["start_time"] = None
    save_tunnel_state(state)

    if stopped_any:
        return True, "Tunnel stopped"
    else:
        return True, "No tunnel was running"

def find_ssh_tunnel_process(port, host_key, direction="remote"):
    """Find SSH tunnel process for the specified port, host, and direction"""
    try:
        ssh_host = SSH_HOSTS[host_key]["hostname"]
        tunnel_flag = "-R" if direction == "remote" else "-L"

        # Look for SSH processes with the specific tunnel pattern
        result = subprocess.run(
            ["pgrep", "-f", f"ssh.*{tunnel_flag} {port}:127.0.0.1:{port}.*{ssh_host}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            pids = [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip()]
            return pids[0] if pids else None
    except Exception:
        pass
    return None

def check_tunnel_status(port, host_key, direction="remote"):
    """Check if tunnel is actually running and update state"""
    state = load_tunnel_state()

    tunnel_key = f"{port}:{direction}@{host_key}"
    if tunnel_key not in state["tunnels"]:
        return False

    tunnel_state = state["tunnels"][tunnel_key]
    
    # First check if we have a PID in our state
    if tunnel_state["running"] and tunnel_state["pid"]:
        if is_process_running(tunnel_state["pid"]):
            return True
        else:
            # Process died, update state
            state["tunnels"][tunnel_key]["running"] = False
            state["tunnels"][tunnel_key]["pid"] = None
            state["tunnels"][tunnel_key]["start_time"] = None
            save_tunnel_state(state)

    # If not in our state, check if there's actually a running tunnel
    actual_pid = find_ssh_tunnel_process(port, host_key, direction)
    if actual_pid:
        # Update our state with the actual running process
        state["tunnels"][tunnel_key]["running"] = True
        state["tunnels"][tunnel_key]["pid"] = actual_pid
        if not state["tunnels"][tunnel_key]["start_time"]:
            state["tunnels"][tunnel_key]["start_time"] = datetime.now().isoformat()
        save_tunnel_state(state)
        return True

    return False

def get_tunnel_uptime(port, host_key, direction="remote"):
    """Get tunnel uptime in minutes"""
    state = load_tunnel_state()

    tunnel_key = f"{port}:{direction}@{host_key}"
    if tunnel_key not in state["tunnels"]:
        return 0

    tunnel_state = state["tunnels"][tunnel_key]

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
    all_ports = get_all_ports(state)

    # Count running tunnels
    running_count = sum(1 for tunnel in state["tunnels"].values() if tunnel.get("running"))

    # Main menu bar display - red if none, green with count if any
    if running_count == 0:
        print("🔴")
    else:
        print(f"🟢 {running_count}")

    print("---")

    # Display each port with submenu for host and direction selection
    for port in all_ports:
        port_has_tunnel = False
        port_tunnels = []

        # Check all possible tunnel combinations for this port
        for host_key in SSH_HOSTS.keys():
            for direction in ["remote", "local"]:
                tunnel_key = f"{port}:{direction}@{host_key}"
                if tunnel_key in state["tunnels"] and state["tunnels"][tunnel_key].get("running"):
                    port_has_tunnel = True
                    port_tunnels.append((host_key, direction, tunnel_key))

        # Port title with status
        if port_has_tunnel:
            print(f"🟢 Port {port}")
            for host_key, direction, tunnel_key in port_tunnels:
                uptime = get_tunnel_uptime(port, host_key, direction)
                uptime_str = f" ({uptime}m)" if uptime > 0 else ""
                dir_symbol = "→" if direction == "remote" else "←"
                dir_label = "Remote (-R)" if direction == "remote" else "Local (-L)"
                pid = state["tunnels"][tunnel_key].get("pid")
                print(f"--{dir_symbol} {SSH_HOSTS[host_key]['display']} {dir_label}{uptime_str}")
                print(f"----Stop | bash={sys.argv[0]} param1=stop param2={port} param3={host_key} param4={direction} terminal=false refresh=true")
                if pid:
                    print(f"----PID: {pid}")
        else:
            print(f"🔴 Port {port}")
            # Show menu to start tunnel
            for host_key, host_info in SSH_HOSTS.items():
                print(f"--{host_info['display']}")
                print(f"----Remote (-R): Expose local → remote | bash={sys.argv[0]} param1=start param2={port} param3={host_key} param4=remote terminal=false refresh=true")
                print(f"----Local (-L): Access remote → local | bash={sys.argv[0]} param1=start param2={port} param3={host_key} param4=local terminal=false refresh=true")

        # Add option to remove temporary port
        if port not in PERMANENT_PORTS and not port_has_tunnel:
            print(f"--Remove Port | bash={sys.argv[0]} param1=remove_port param2={port} terminal=false refresh=true")

        print("---")

    # Add custom port option
    print(f"➕ Add Custom Port | bash={sys.argv[0]} param1=add_port terminal=false refresh=false")
    print("---")

    # Connection info
    print("Available Hosts:")
    for host_key, host_info in SSH_HOSTS.items():
        print(f"--{host_info['display']}: {host_info['hostname']}")
    print("---")
    print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# -----------------------------------
# Action Handlers
# -----------------------------------
def handle_start_tunnel(port, host_key, direction="remote"):
    """Handle starting a tunnel"""
    if host_key not in SSH_HOSTS:
        print(f"❌ Invalid host: {host_key}")
        return

    # Check if already running
    if check_tunnel_status(port, host_key, direction):
        print(f"✅ Tunnel for port {port} to {host_key} is already running")
        return

    success, result = start_ssh_tunnel(port, host_key, direction)

    if success:
        # Update state
        state = load_tunnel_state()
        tunnel_key = f"{port}:{direction}@{host_key}"
        state["tunnels"][tunnel_key] = {
            "running": True,
            "pid": result,
            "start_time": datetime.now().isoformat()
        }
        save_tunnel_state(state)
        dir_label = "Remote (-R)" if direction == "remote" else "Local (-L)"
        print(f"✅ Started {dir_label} tunnel for port {port} to {SSH_HOSTS[host_key]['display']} (PID: {result})")
    else:
        print(f"❌ Failed to start tunnel for port {port}: {result}")

def handle_stop_tunnel(port, host_key, direction="remote"):
    """Handle stopping a tunnel"""
    if host_key not in SSH_HOSTS:
        print(f"❌ Invalid host: {host_key}")
        return

    success, result = stop_ssh_tunnel(port, host_key, direction)

    if success:
        dir_label = "Remote (-R)" if direction == "remote" else "Local (-L)"
        print(f"✅ Stopped {dir_label} tunnel for port {port} from {SSH_HOSTS[host_key]['display']}")
    else:
        print(f"❌ Failed to stop tunnel for port {port}: {result}")

def handle_add_port():
    """Handle adding a custom port"""
    import subprocess
    result = subprocess.run(
        ["osascript", "-e", 'display dialog "Enter port number:" default answer ""'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        # Extract port from osascript output
        output = result.stdout.strip()
        if "button returned:OK, text returned:" in output:
            port = output.split("text returned:")[1].strip()
            if port.isdigit():
                state = load_tunnel_state()
                if port not in state["temporary_ports"]:
                    state["temporary_ports"].append(port)
                    save_tunnel_state(state)
                    print(f"✅ Added port {port}")
                else:
                    print(f"ℹ️ Port {port} already exists")
            else:
                print("❌ Invalid port number")
    else:
        print("❌ Cancelled")

def handle_remove_port(port):
    """Handle removing a temporary port"""
    state = load_tunnel_state()
    if port in state.get("temporary_ports", []):
        state["temporary_ports"].remove(port)
        save_tunnel_state(state)
        print(f"✅ Removed port {port}")
    else:
        print(f"❌ Port {port} not found in temporary ports")

# -----------------------------------
# Main Execution
# -----------------------------------
if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "start" and len(sys.argv) > 4:
            handle_start_tunnel(sys.argv[2], sys.argv[3], sys.argv[4])
        elif command == "stop" and len(sys.argv) > 4:
            handle_stop_tunnel(sys.argv[2], sys.argv[3], sys.argv[4])
        elif command == "add_port":
            handle_add_port()
        elif command == "remove_port" and len(sys.argv) > 2:
            handle_remove_port(sys.argv[2])
        else:
            print("❌ Invalid command")
    else:
        # Render the menu
        render_menu()
