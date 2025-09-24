#!/usr/bin/env python3
# <bitbar.title>Timer</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>AC</bitbar.author>
# <bitbar.desc>Timer with 5-minute increments up to 1 hour, flashes rapidly when complete</bitbar.desc>
# <bitbar.dependencies>python3</bitbar.dependencies>

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# -----------------------------------
# Configuration
# -----------------------------------
CACHE_DIR = Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache")))
CACHE_FILE = CACHE_DIR / "swiftbar_timer_cache.json"
REFRESH_INTERVAL = 1  # Refresh every 1 second for accurate timing

# Timer states
TIMER_STATES = {
    'STOPPED': 'stopped',
    'RUNNING': 'running',
    'PAUSED': 'paused',
    'COMPLETED': 'completed',
    'FLASHING': 'flashing'
}

# -----------------------------------
# Cache Functions
# -----------------------------------
def load_timer_state():
    """Load timer state from cache"""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    
    # Default state
    return {
        'state': TIMER_STATES['STOPPED'],
        'start_time': None,
        'duration_minutes': 0,
        'end_time': None,
        'paused_time': None,
        'total_paused_duration': 0,
        'flash_count': 0,
        'last_flash': 0
    }

def save_timer_state(state):
    """Save timer state to cache"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception:
        pass

# -----------------------------------
# Timer Logic
# -----------------------------------
def start_timer(duration_minutes):
    """Start a timer for the specified duration"""
    state = load_timer_state()
    state['state'] = TIMER_STATES['RUNNING']
    state['start_time'] = time.time()
    state['duration_minutes'] = duration_minutes
    state['end_time'] = state['start_time'] + (duration_minutes * 60)
    state['flash_count'] = 0
    state['last_flash'] = 0
    save_timer_state(state)

def pause_timer():
    """Pause the current timer"""
    state = load_timer_state()
    if state['state'] == TIMER_STATES['RUNNING']:
        state['state'] = TIMER_STATES['PAUSED']
        state['paused_time'] = time.time()
        save_timer_state(state)

def resume_timer():
    """Resume the paused timer"""
    state = load_timer_state()
    if state['state'] == TIMER_STATES['PAUSED']:
        # Calculate total paused duration and adjust end time
        if state['paused_time']:
            paused_duration = time.time() - state['paused_time']
            # Initialize total_paused_duration if it doesn't exist
            if 'total_paused_duration' not in state:
                state['total_paused_duration'] = 0
            state['total_paused_duration'] += paused_duration
            state['end_time'] += paused_duration
            state['paused_time'] = None
        
        state['state'] = TIMER_STATES['RUNNING']
        save_timer_state(state)

def stop_timer():
    """Stop the current timer"""
    state = load_timer_state()
    state['state'] = TIMER_STATES['STOPPED']
    state['start_time'] = None
    state['duration_minutes'] = 0
    state['end_time'] = None
    state['paused_time'] = None
    state['total_paused_duration'] = 0
    state['flash_count'] = 0
    state['last_flash'] = 0
    save_timer_state(state)

def dismiss_timer():
    """Dismiss the completed timer"""
    state = load_timer_state()
    state['state'] = TIMER_STATES['STOPPED']
    state['start_time'] = None
    state['duration_minutes'] = 0
    state['end_time'] = None
    state['paused_time'] = None
    state['total_paused_duration'] = 0
    state['flash_count'] = 0
    state['last_flash'] = 0
    save_timer_state(state)

def get_remaining_time():
    """Get remaining time in seconds"""
    state = load_timer_state()
    
    if state['state'] not in [TIMER_STATES['RUNNING'], TIMER_STATES['PAUSED']]:
        return 0
    
    if state['state'] == TIMER_STATES['PAUSED']:
        # If paused, return the remaining time when it was paused
        if state['paused_time'] and state['end_time']:
            remaining = state['end_time'] - state['paused_time']
            return max(0, int(remaining))
        return 0
    
    current_time = time.time()
    remaining = state['end_time'] - current_time
    
    if remaining <= 0:
        # Timer completed, start flashing
        state['state'] = TIMER_STATES['COMPLETED']
        save_timer_state(state)
        return 0
    
    return max(0, int(remaining))

def format_time(seconds):
    """Format seconds as MM:SS"""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def should_flash():
    """Determine if the timer should be flashing"""
    state = load_timer_state()
    
    if state['state'] not in [TIMER_STATES['COMPLETED'], TIMER_STATES['FLASHING']]:
        return False
    
    current_time = time.time()
    
    # Flash every 0.5 seconds (rapid flashing)
    if current_time - state['last_flash'] >= 0.5:
        state['last_flash'] = current_time
        state['flash_count'] += 1
        # Alternate between completed and flashing states
        if state['state'] == TIMER_STATES['COMPLETED']:
            state['state'] = TIMER_STATES['FLASHING']
        else:
            state['state'] = TIMER_STATES['COMPLETED']
        save_timer_state(state)
    
    return state['state'] == TIMER_STATES['FLASHING']

# -----------------------------------
# Menu Rendering
# -----------------------------------
def render_menu():
    """Render the SwiftBar menu"""
    state = load_timer_state()
    current_time = time.time()
    
    # Check if timer should be completed
    if state['state'] == TIMER_STATES['RUNNING']:
        remaining = get_remaining_time()
        if remaining == 0:
            state = load_timer_state()  # Reload state after completion
    
    # Main menu bar display
    if state['state'] == TIMER_STATES['STOPPED']:
        print("⏱️")
    elif state['state'] == TIMER_STATES['RUNNING']:
        remaining = get_remaining_time()
        if remaining > 0:
            print(f"⏱️ {format_time(remaining)}")
        else:
            print("⏱️ 00:00")
    elif state['state'] == TIMER_STATES['PAUSED']:
        remaining = get_remaining_time()
        print(f"⏸️ {format_time(remaining)}")
    elif state['state'] in [TIMER_STATES['COMPLETED'], TIMER_STATES['FLASHING']]:
        if should_flash():
            print("⏱️ 00:00")  # Flash between showing and not showing
        else:
            print("⏱️ 00:00")
    
    print("---")
    
    # Timer controls
    if state['state'] == TIMER_STATES['STOPPED']:
        # Show timer duration options (5-minute increments up to 1 hour)
        durations = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
        for duration in durations:
            print(f"Start {duration}min Timer | bash={sys.argv[0]} param1=start param2={duration} terminal=false refresh=true")
    elif state['state'] == TIMER_STATES['RUNNING']:
        remaining = get_remaining_time()
        if remaining > 0:
            print(f"⏱️ {format_time(remaining)} remaining")
            print(f"Pause Timer | bash={sys.argv[0]} param1=pause terminal=false refresh=true")
            print(f"Stop Timer | bash={sys.argv[0]} param1=stop terminal=false refresh=true")
        else:
            print("⏱️ Timer Complete!")
            print(f"Dismiss | bash={sys.argv[0]} param1=dismiss terminal=false refresh=true")
    elif state['state'] == TIMER_STATES['PAUSED']:
        remaining = get_remaining_time()
        print(f"⏸️ {format_time(remaining)} paused")
        print(f"Resume Timer | bash={sys.argv[0]} param1=resume terminal=false refresh=true")
        print(f"Stop Timer | bash={sys.argv[0]} param1=stop terminal=false refresh=true")
    elif state['state'] in [TIMER_STATES['COMPLETED'], TIMER_STATES['FLASHING']]:
        print("⏱️ Timer Complete!")
        print(f"Dismiss | bash={sys.argv[0]} param1=dismiss terminal=false refresh=true")
    
    print("---")
    print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# -----------------------------------
# Action Handlers
# -----------------------------------
def handle_start_timer(duration_str):
    """Handle starting a timer"""
    try:
        duration = int(duration_str)
        if 5 <= duration <= 60 and duration % 5 == 0:
            start_timer(duration)
            print(f"✅ Started {duration}-minute timer")
        else:
            print(f"❌ Invalid duration. Must be 5-60 minutes in 5-minute increments")
    except ValueError:
        print(f"❌ Invalid duration format")

def handle_pause_timer():
    """Handle pausing the timer"""
    pause_timer()
    print("⏸️ Timer paused")

def handle_resume_timer():
    """Handle resuming the timer"""
    resume_timer()
    print("▶️ Timer resumed")

def handle_stop_timer():
    """Handle stopping the timer"""
    stop_timer()
    print("✅ Timer stopped")

def handle_dismiss_timer():
    """Handle dismissing the completed timer"""
    dismiss_timer()
    print("✅ Timer dismissed")

# -----------------------------------
# Main Execution
# -----------------------------------
if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "start" and len(sys.argv) > 2:
            handle_start_timer(sys.argv[2])
        elif command == "pause":
            handle_pause_timer()
        elif command == "resume":
            handle_resume_timer()
        elif command == "stop":
            handle_stop_timer()
        elif command == "dismiss":
            handle_dismiss_timer()
        else:
            print("❌ Invalid command")
    else:
        # Render the menu
        render_menu()
