#!/usr/bin/env python3
# <bitbar.title>Hamilton County 911 Calls</bitbar.title>
# <bitbar.version>v1.1</bitbar.version>
# <bitbar.author>AC</bitbar.author>
# <bitbar.desc>Display Hamilton County 911 active calls from hc911server.com API</bitbar.desc>
# <bitbar.dependencies>python3</bitbar.dependencies>

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# -----------------------------------
# Configuration
# -----------------------------------
API_URL = "https://hc911server.com/api/calls"
AUTH_TOKEN = os.getenv("HC911_AUTH_TOKEN", "my-secure-token")
MAX_CALLS_DISPLAY = int(os.getenv("HC911_MAX_CALLS", "150"))

# Cache configuration
CACHE_DIR = Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache")))
CACHE_FILE = CACHE_DIR / "swiftbar_hc911_cache.json"
CACHE_DURATION = 25  # Cache for 25 seconds (refresh every 30s)

# Status icons and colors
STATUS_ICONS = {
    "Queued": "🟡",
    "Enroute": "🟠",
    "On Scene": "🔴",
    "At Hospital": "🏥",
    "Stacked": "📚",
    "Transporting": "🚑"
}

PRIORITY_ICONS = {
    "PRI 1": "🚨",
    "PRI 2": "⚠️",
    "PRI 3": "🔵",
    "PRI 4": "⚪"
}

AGENCY_ICONS = {
    "EMS": "🚑",
    "Fire": "🚒",
    "Law": "👮",
    "HC911": "📡"
}

# -----------------------------------
# HTTP Request Function
# -----------------------------------
def fetch_911_calls():
    """Fetch 911 calls from the Hamilton County API"""
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://www.hamiltontn911.gov',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.hamiltontn911.gov/',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'x-frontend-auth': AUTH_TOKEN
    }

    try:
        request = urllib.request.Request(API_URL, headers=headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except urllib.error.HTTPError as e:
        print(f"DEBUG: HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"DEBUG: URL Error: {e.reason}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON Decode Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"DEBUG: Unexpected error: {e}", file=sys.stderr)
        return None

# -----------------------------------
# Cache Functions
# -----------------------------------
def load_cache():
    """Load cached data if it exists and is still fresh"""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)

            # Check if cache is still fresh
            cache_time = cache.get('timestamp', 0)
            current_time = datetime.now().timestamp()

            if current_time - cache_time < CACHE_DURATION:
                print(f"DEBUG: Using cached data from {datetime.fromtimestamp(cache_time)}", file=sys.stderr)
                return cache.get('data')
    except Exception as e:
        print(f"DEBUG: Error loading cache: {e}", file=sys.stderr)

    return None

def save_cache(data):
    """Save data to cache"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache = {
            'data': data,
            'timestamp': datetime.now().timestamp()
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"DEBUG: Error saving cache: {e}", file=sys.stderr)

# -----------------------------------
# Data Processing
# -----------------------------------
def get_calls_data():
    """Get 911 calls data, using cache if available"""
    # Try to load from cache first
    cached_data = load_cache()
    if cached_data is not None:
        return cached_data

    # Fetch fresh data
    print("DEBUG: Fetching fresh data from API", file=sys.stderr)
    data = fetch_911_calls()

    if data is not None:
        save_cache(data)
        return data

    # If fresh fetch failed, try to use stale cache
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                print("DEBUG: Using stale cache data due to API failure", file=sys.stderr)
                return cache.get('data')
    except Exception:
        pass

    return None

def parse_datetime(dt_string):
    """Parse ISO datetime string to readable format"""
    try:
        if dt_string and dt_string != "1900-01-01T00:00:00.000Z":
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            return dt.strftime("%H:%M")
    except:
        pass
    return ""

def format_call_info(call):
    """Format call information for display"""
    status = call.get('status', 'Unknown')
    call_type = call.get('type_description', call.get('type', 'Unknown'))
    location = call.get('location', 'Unknown Location')
    premise = call.get('premise', '')
    priority = call.get('priority', '')
    agency_type = call.get('agency_type', '')
    jurisdiction = call.get('jurisdiction', '')
    zone = call.get('zone', '')
    battalion = call.get('battalion', '')
    creation = parse_datetime(call.get('creation'))
    crossstreets = call.get('crossstreets', '')

    # Clean up premise
    if premise and premise.startswith('@'):
        premise = premise[1:]

    # Format location with premise
    full_location = location
    if premise and premise.strip():
        full_location = f"{location} ({premise.strip()})"

    return {
        'status': status,
        'type': call_type,
        'location': full_location,
        'priority': priority,
        'agency_type': agency_type,
        'jurisdiction': jurisdiction,
        'zone': zone,
        'battalion': battalion,
        'creation': creation,
        'crossstreets': crossstreets,
        'stacked': call.get('stacked', False)
    }

def get_summary_stats(calls):
    """Get summary statistics for menu bar display"""
    stats = {
        'total': len(calls),
        'priorities': defaultdict(int),
        'statuses': defaultdict(int),
        'agencies': defaultdict(int)
    }

    for call in calls:
        priority = call.get('priority', '')
        status = call.get('status', '')
        agency = call.get('agency_type', '')

        if priority:
            stats['priorities'][priority] += 1
        if status:
            stats['statuses'][status] += 1
        if agency:
            stats['agencies'][agency] += 1

    return stats

def count_recent_calls(calls, minutes=10):
    """Count calls created in the last N minutes"""
    if not calls:
        return 0

    current_time = datetime.now(timezone.utc)
    cutoff_time = current_time - timedelta(minutes=minutes)

    recent_count = 0
    for call in calls:
        creation_str = call.get('creation')
        if creation_str and creation_str != "1900-01-01T00:00:00.000Z":
            try:
                creation_time = datetime.fromisoformat(creation_str.replace('Z', '+00:00'))
                if creation_time >= cutoff_time:
                    recent_count += 1
            except:
                continue

    return recent_count

def create_maps_link(call):
    """Create Apple Maps link from latitude/longitude"""
    lat = call.get('latitude')
    lng = call.get('longitude')
    if lat and lng:
        return f"https://maps.apple.com/?q={lat},{lng}"
    return None

# -----------------------------------
# Menu Rendering
# -----------------------------------
def render_menu():
    """Render the SwiftBar menu"""
    calls_data = get_calls_data()

    if calls_data is None:
        print("hc911 ❌")
        print("---")
        print("Error fetching 911 calls")
        print("Check network connection")
        return

    if not isinstance(calls_data, list):
        print("hc911 ❓")
        print("---")
        print("Unexpected data format")
        return

    # Limit calls and get stats
    calls = calls_data[:MAX_CALLS_DISPLAY]
    stats = get_summary_stats(calls)

    # Create simple menu bar title with just new calls count
    recent_count = count_recent_calls(calls_data, 10)
    if recent_count > 0:
        menu_title = f"hc911 {recent_count}"
    else:
        menu_title = "hc911"

    print(menu_title)
    print("---")

    if stats['total'] == 0:
        print("No active calls")
        return

    # Summary section
    print("📊 Summary")
    print(f"--Total Calls: {stats['total']}")
    pri1_count = stats['priorities'].get('PRI 1', 0)
    pri2_count = stats['priorities'].get('PRI 2', 0)
    if pri1_count > 0:
        print(f"--Priority 1: {pri1_count}")
    if pri2_count > 0:
        print(f"--Priority 2: {pri2_count}")
    print(f"--On Scene: {stats['statuses'].get('On Scene', 0)}")
    print(f"--Enroute: {stats['statuses'].get('Enroute', 0)}")
    print("---")

    # Show 5 most recent calls inline with full details (top-level, no dropdowns)
    recent_calls = sorted(calls, key=lambda x: x.get('creation', ''), reverse=True)[:5]
    if recent_calls:
        print("🕒 Most Recent 5 Calls")
        for i, call in enumerate(recent_calls):
            formatted_call = format_call_info(call)
            maps_link = create_maps_link(call)

            # Main call info line
            status_icon = STATUS_ICONS.get(formatted_call['status'], '⚫')
            priority_icon = PRIORITY_ICONS.get(formatted_call['priority'], '⚫')
            agency_icon = AGENCY_ICONS.get(formatted_call['agency_type'], '📻')
            stacked_indicator = " 📚" if formatted_call['stacked'] else ""

            # Top-level items (no -- prefix)
            main_line = f"{status_icon} {priority_icon} {formatted_call['type']}{stacked_indicator}"
            print(main_line)

            location_line = f"📍 {formatted_call['location']}"
            print(location_line)

            if maps_link:
                print(f"🗺️ Open in Maps | href={maps_link}")

            if formatted_call['creation']:
                print(f"🕐 {formatted_call['creation']}")

            if formatted_call['jurisdiction']:
                print(f"{agency_icon} {formatted_call['jurisdiction']}")

            if formatted_call['battalion']:
                print(f"🎯 {formatted_call['battalion']}")

            if formatted_call['crossstreets'] and formatted_call['crossstreets'] != 'No Cross Street':
                print(f"🛣️ {formatted_call['crossstreets']}")

            if i < len(recent_calls) - 1:
                print("---")

        print("---")

    # Group calls by priority and status for better organization
    priority_groups = defaultdict(list)
    for call in calls:
        priority = call.get('priority', 'Unknown')
        priority_groups[priority].append(call)

    # Display calls by priority order
    priority_order = ['PRI 1', 'PRI 2', 'PRI 3', 'PRI 4', '']

    for priority in priority_order:
        if priority in priority_groups and priority_groups[priority]:
            # Group header
            pri_icon = PRIORITY_ICONS.get(priority, '⚫')
            if priority:
                print(f"{pri_icon} {priority} ({len(priority_groups[priority])} calls)")
            else:
                print(f"⚫ Other ({len(priority_groups[priority])} calls)")

            # Sort calls within priority by status importance
            status_order = ['On Scene', 'Transporting', 'Enroute', 'Queued', 'Stacked', 'At Hospital']
            calls_by_status = defaultdict(list)
            for call in priority_groups[priority]:
                status = call.get('status', 'Unknown')
                calls_by_status[status].append(call)

            for status in status_order:
                if status in calls_by_status:
                    for call in calls_by_status[status]:
                        formatted_call = format_call_info(call)
                        maps_link = create_maps_link(call)

                        # Status and type
                        status_icon = STATUS_ICONS.get(formatted_call['status'], '⚫')
                        agency_icon = AGENCY_ICONS.get(formatted_call['agency_type'], '📻')

                        stacked_indicator = " 📚" if formatted_call['stacked'] else ""

                        main_line = f"--{status_icon} {formatted_call['type']}{stacked_indicator}"
                        print(main_line)

                        location_line = f"----📍 {formatted_call['location']}"
                        print(location_line)

                        if maps_link:
                            print(f"----🗺️ Open in Maps | href={maps_link}")

                        if formatted_call['creation']:
                            print(f"----🕐 {formatted_call['creation']}")

                        if formatted_call['jurisdiction']:
                            print(f"----{agency_icon} {formatted_call['jurisdiction']}")

                        if formatted_call['battalion']:
                            print(f"----🎯 {formatted_call['battalion']}")

                        if formatted_call['crossstreets'] and formatted_call['crossstreets'] != 'No Cross Street':
                            print(f"----🛣️ {formatted_call['crossstreets']}")

            print("-----")

    # Show total if more calls exist than displayed
    if len(calls_data) > MAX_CALLS_DISPLAY:
        print("---")
        print(f"... and {len(calls_data) - MAX_CALLS_DISPLAY} more calls not shown")

    print("---")
    print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Hamilton County 911 | href=https://www.hamiltontn911.gov")

# -----------------------------------
# Main Execution
# -----------------------------------
if __name__ == "__main__":
    render_menu()
