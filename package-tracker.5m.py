#!/usr/bin/env python3
# <bitbar.title>Package Tracker</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>AC</bitbar.author>
# <bitbar.desc>Track packages from UPS, USPS, FedEx, and DHL with status, location, and delivery date</bitbar.desc>
# <bitbar.dependencies>python3,requests,beautifulsoup4</bitbar.dependencies>

import os
import sys
import json
import time
import re
import subprocess
import urllib.request
import urllib.error
import webbrowser
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# -----------------------------------
# Configuration
# -----------------------------------
CACHE_DIR = Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache")))
CACHE_FILE = CACHE_DIR / "swiftbar_package_tracker_cache.json"
CACHE_DURATION = 300  # Cache for 5 minutes

# Tracking numbers storage file
TRACKING_FILE = Path(__file__).parent / "tracking_numbers.json"

# Carrier detection patterns
CARRIER_PATTERNS = {
    'UPS': [
        r'^1Z[0-9A-Z]{16}$',
        r'^1Z[0-9A-Z]{18}$',
        r'^T[0-9]{10}$'
    ],
    'USPS': [
        r'^[0-9]{20}$',
        r'^[0-9]{22}$',
        r'^[A-Z]{2}[0-9]{9}US$',
        r'^[0-9]{13}$',
        r'^[0-9]{15}$'
    ],
    'FedEx': [
        r'^[0-9]{12}$',
        r'^[0-9]{14}$',
        r'^[0-9]{15}$',
        r'^[0-9]{20}$',
        r'^[0-9]{22}$'
    ],
    'DHL': [
        r'^[0-9]{10}$',
        r'^[0-9]{11}$',
        r'^[0-9]{12}$',
        r'^JD[0-9]{18}$',
        r'^[0-9]{9}$'
    ]
}

# Status icons and colors
STATUS_ICONS = {
    'delivered': '✅',
    'in_transit': '🚚',
    'out_for_delivery': '🚛',
    'exception': '⚠️',
    'pending': '⏳',
    'unknown': '❓'
}

STATUS_COLORS = {
    'delivered': 'green',
    'in_transit': 'blue',
    'out_for_delivery': 'orange',
    'exception': 'red',
    'pending': 'yellow',
    'unknown': 'gray'
}

# Tracking URLs for browser opening
TRACKING_URLS = {
    'UPS': 'https://www.ups.com/track?tracknum={}',
    'USPS': 'https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={}',
    'FedEx': 'https://www.fedex.com/fedextrack/?trknbr={}',
    'DHL': 'https://www.dhl.com/us-en/home/tracking.html?track-id={}'
}

# Alternative tracking APIs (free tiers)
# Using AfterShip API (free tier) as primary
AFTERSHIP_API_URL = 'https://api.aftership.com/v4/trackings'
AFTERSHIP_API_KEY = 'free'  # Using free tier

# Ship24 as fallback
SHIP24_API_URL = 'https://api.ship24.com/public/v1/track'
SHIP24_API_KEY = 'free'

# -----------------------------------
# Cache Functions
# -----------------------------------
def load_cache():
    """Load cached tracking data if it exists and is still fresh"""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
            
            # Check if cache is still fresh
            cache_time = cache.get('timestamp', 0)
            current_time = time.time()
            
            if current_time - cache_time < CACHE_DURATION:
                return cache.get('data', {})
    except Exception as e:
        print(f"DEBUG: Error loading cache: {e}", file=sys.stderr)
    
    return {}

def save_cache(data):
    """Save tracking data to cache"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache = {
            'data': data,
            'timestamp': time.time()
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"DEBUG: Error saving cache: {e}", file=sys.stderr)

# -----------------------------------
# Tracking Number Management
# -----------------------------------
def load_tracking_numbers():
    """Load tracking numbers from file"""
    try:
        if TRACKING_FILE.exists():
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"DEBUG: Error loading tracking numbers: {e}", file=sys.stderr)
    
    return []

def save_tracking_numbers(tracking_numbers):
    """Save tracking numbers to file"""
    try:
        with open(TRACKING_FILE, 'w') as f:
            json.dump(tracking_numbers, f, indent=2)
    except Exception as e:
        print(f"DEBUG: Error saving tracking numbers: {e}", file=sys.stderr)

def detect_carrier(tracking_number):
    """Detect carrier based on tracking number format"""
    for carrier, patterns in CARRIER_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, tracking_number.upper()):
                return carrier
    return 'Unknown'

# -----------------------------------
# Web Scraping Functions
# -----------------------------------
def fetch_tracking_info(tracking_number, carrier):
    """Fetch tracking information using real APIs and web scraping - NO FAKE DATA"""
    print(f"DEBUG: Fetching data for {carrier} {tracking_number}", file=sys.stderr)
    
    # Try UPS API first
    if carrier == 'UPS':
        try:
            result = fetch_ups_api_tracking(tracking_number)
            if result:
                return result
        except Exception as e:
            print(f"DEBUG: UPS API failed: {e}", file=sys.stderr)
    
    # Try web scraping
    try:
        result = fetch_web_tracking(tracking_number, carrier)
        if result and result.get('status') != 'unknown':
            return result
    except Exception as e:
        print(f"DEBUG: Web scraping failed: {e}", file=sys.stderr)
    
    # If all methods fail, return None (no fake data)
    print(f"DEBUG: Could not fetch real data for {carrier} {tracking_number}", file=sys.stderr)
    return None

def fetch_ship24_tracking(tracking_number):
    """Fetch tracking information using Ship24 API"""
    try:
        headers = {
            'Authorization': f'Bearer {SHIP24_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'trackingNumber': tracking_number
        }
        
        request = urllib.request.Request(
            SHIP24_API_URL,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get('data') and result['data'].get('trackings'):
                tracking = result['data']['trackings'][0]
                events = tracking.get('events', [])
                
                if events:
                    latest_event = events[0]
                    status_text = latest_event.get('status', '').lower()
                    
                    # Map Ship24 status to our status
                    if 'delivered' in status_text:
                        status = 'delivered'
                    elif 'out for delivery' in status_text or 'on vehicle' in status_text:
                        status = 'out_for_delivery'
                    elif 'in transit' in status_text or 'processed' in status_text:
                        status = 'in_transit'
                    elif 'exception' in status_text or 'delay' in status_text:
                        status = 'exception'
                    else:
                        status = 'unknown'
                    
                    location = latest_event.get('location', 'Unknown')
                    delivery_date = latest_event.get('date', 'Unknown')
                    
                    return {
                        'status': status,
                        'location': location,
                        'delivery_date': delivery_date,
                        'last_updated': datetime.now().isoformat()
                    }
        
        return None
    except Exception as e:
        print(f"DEBUG: Ship24 API error: {e}", file=sys.stderr)
        return None

def fetch_ups_api_tracking(tracking_number):
    """Fetch UPS tracking information using curl command directly"""
    try:
        # Use the exact curl command that works
        curl_cmd = [
            'curl', '-s',
            'https://webapis.ups.com/track/api/Track/GetStatus?loc=en_US',
            '-H', 'accept: application/json, text/plain, */*',
            '-H', 'accept-language: en-US,en;q=0.9',
            '-H', 'cache-control: no-cache',
            '-H', 'content-type: application/json',
            '-H', 'dnt: 1',
            '-H', 'origin: https://www.ups.com',
            '-H', 'pragma: no-cache',
            '-H', 'priority: u=1, i',
            '-H', 'sec-ch-ua: "Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            '-H', 'sec-ch-ua-mobile: ?0',
            '-H', 'sec-ch-ua-platform: "macOS"',
            '-H', 'sec-fetch-dest: empty',
            '-H', 'sec-fetch-mode: cors',
            '-H', 'sec-fetch-site: same-site',
            '-H', 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            '-H', 'x-xsrf-token: CfDJ8Jcj9GhlwkdBikuRYzfhrpLHC_IjS1tqIW5zb-NGlIiyOWk3G9YMHGBGqfjM0xKzDoH6AH3MkGA4wK16UEVh3exNJfRnHwciNENBc2mtGTqEeDZ8R_cGsY_88DC7U-e-n-yyzMQoVjYECFxeLp-p3hQ',
            '--data-raw', f'{{"Locale":"en_US","TrackingNumber":["{tracking_number.lower()}"],"isBarcodeScanned":false,"Requester":"st/trackdetails","returnToValue":""}}'
        ]
        
        print(f"DEBUG: Running curl command for {tracking_number}", file=sys.stderr)
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print(f"DEBUG: Curl response length: {len(result.stdout)}", file=sys.stderr)
            print(f"DEBUG: Curl response: {result.stdout}", file=sys.stderr)
            data = json.loads(result.stdout)
            
            if data.get('trackDetails') and len(data['trackDetails']) > 0:
                track_detail = data['trackDetails'][0]
                
                # Get package status
                package_status = track_detail.get('packageStatus', '')
                print(f"DEBUG: Package status: {package_status}", file=sys.stderr)
                
                # Map UPS status to our status
                if 'delivered' in package_status.lower():
                    status = 'delivered'
                elif 'out for delivery' in package_status.lower():
                    status = 'out_for_delivery'
                elif 'in transit' in package_status.lower() or 'on the way' in package_status.lower():
                    status = 'in_transit'
                elif 'exception' in package_status.lower() or 'delay' in package_status.lower():
                    status = 'exception'
                else:
                    status = 'in_transit'  # Default to in transit for UPS
                
                # Get location from shipment progress activities
                location = 'Unknown'
                delivery_date = 'Unknown'
                
                shipment_progress = track_detail.get('shipmentProgressActivities', [])
                if shipment_progress:
                    latest_activity = shipment_progress[0]
                    location = latest_activity.get('location', 'Unknown')
                    print(f"DEBUG: Location: {location}", file=sys.stderr)
                    
                    # Get delivery date from scheduled delivery
                    if 'scheduledDeliveryDateDetail' in track_detail:
                        sdd = track_detail['scheduledDeliveryDateDetail']
                        month = sdd.get('monthCMSKey', '').replace('cms.stapp.', '')
                        day = sdd.get('dayNum', '')
                        if month and day:
                            delivery_date = f"{month.capitalize()} {day}"
                            print(f"DEBUG: Delivery date: {delivery_date}", file=sys.stderr)
                
                return {
                    'status': status,
                    'location': location,
                    'delivery_date': delivery_date,
                    'last_updated': datetime.now().isoformat()
                }
        else:
            print(f"DEBUG: Curl failed with return code {result.returncode}", file=sys.stderr)
            print(f"DEBUG: Curl stderr: {result.stderr}", file=sys.stderr)
        
        return None
    except Exception as e:
        print(f"DEBUG: UPS API error: {e}", file=sys.stderr)
        return None

def fetch_web_tracking(tracking_number, carrier):
    """Improved web scraping method with better reliability"""
    try:
        # Try UPS API first
        if carrier == 'UPS':
            api_result = fetch_ups_api_tracking(tracking_number)
            if api_result:
                return api_result
        
        # Fallback to web scraping for other carriers or if API fails
        if carrier in TRACKING_URLS:
            url = TRACKING_URLS[carrier].format(tracking_number)
        else:
            return None
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            html = response.read().decode('utf-8')
            
            # More comprehensive status detection
            html_lower = html.lower()
            
            # Check for delivered status
            if any(phrase in html_lower for phrase in [
                'delivered', 'delivery complete', 'package delivered',
                'successfully delivered', 'delivery successful'
            ]):
                status = 'delivered'
            # Check for out for delivery
            elif any(phrase in html_lower for phrase in [
                'out for delivery', 'on vehicle for delivery', 'out for delivery today',
                'on truck for delivery', 'out for delivery now'
            ]):
                status = 'out_for_delivery'
            # Check for in transit
            elif any(phrase in html_lower for phrase in [
                'in transit', 'processed', 'on the way', 'in progress',
                'shipped', 'departed', 'arrived at', 'processed through'
            ]):
                status = 'in_transit'
            # Check for exceptions
            elif any(phrase in html_lower for phrase in [
                'exception', 'delay', 'problem', 'issue', 'held',
                'weather delay', 'delivery exception'
            ]):
                status = 'exception'
            # Check for pending
            elif any(phrase in html_lower for phrase in [
                'pending', 'label created', 'ready for pickup',
                'awaiting pickup', 'processing'
            ]):
                status = 'pending'
            else:
                status = 'unknown'
            
            # Try to extract location and delivery date (basic parsing)
            location = 'Unknown'
            delivery_date = 'Unknown'
            
            # Look for common location patterns
            import re
            location_patterns = [
                r'at\s+([A-Za-z\s,]+?)(?:\s+on\s|\s+at\s|\s+$|\.)',
                r'arrived\s+at\s+([A-Za-z\s,]+?)(?:\s+on\s|\s+at\s|\s+$|\.)',
                r'processed\s+through\s+([A-Za-z\s,]+?)(?:\s+on\s|\s+at\s|\s+$|\.)'
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, html_lower)
                if match:
                    location = match.group(1).strip().title()
                    break
            
            # Look for delivery date patterns
            date_patterns = [
                r'delivery\s+date[:\s]+([A-Za-z0-9\s,]+?)(?:\s|$)',
                r'expected\s+delivery[:\s]+([A-Za-z0-9\s,]+?)(?:\s|$)',
                r'delivered\s+on\s+([A-Za-z0-9\s,]+?)(?:\s|$)'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, html_lower)
                if match:
                    delivery_date = match.group(1).strip()
                    break
            
            return {
                'status': status,
                'location': location,
                'delivery_date': delivery_date,
                'last_updated': datetime.now().isoformat()
            }
    except Exception as e:
        print(f"DEBUG: Web scraping error for {carrier}: {e}", file=sys.stderr)
        return None

def get_tracking_url(tracking_number, carrier):
    """Get the tracking URL for opening in browser"""
    if carrier in TRACKING_URLS:
        return TRACKING_URLS[carrier].format(tracking_number)
    return None

# -----------------------------------
# Data Processing
# -----------------------------------
def get_tracking_data():
    """Get tracking data for all packages, using cache if available"""
    # Try to load from cache first
    cached_data = load_cache()
    if cached_data:
        return cached_data
    
    # Fetch fresh data
    tracking_numbers = load_tracking_numbers()
    tracking_data = {}
    
    for item in tracking_numbers:
        tracking_number = item.get('tracking_number', '')
        carrier = item.get('carrier', '')
        name = item.get('name', '')
        
        if not tracking_number or not carrier:
            continue
        
        print(f"DEBUG: Fetching data for {carrier} {tracking_number}", file=sys.stderr)
        data = fetch_tracking_info(tracking_number, carrier)
        
        if data:
            tracking_data[tracking_number] = {
                'carrier': carrier,
                'name': name,
                'status': data['status'],
                'location': data['location'],
                'delivery_date': data['delivery_date'],
                'last_updated': data['last_updated']
            }
        else:
            # Use cached data if available, otherwise set to unknown
            tracking_data[tracking_number] = {
                'carrier': carrier,
                'name': name,
                'status': 'unknown',
                'location': 'Unknown',
                'delivery_date': 'Unknown',
                'last_updated': datetime.now().isoformat()
            }
    
    # Save to cache
    save_cache(tracking_data)
    return tracking_data

# -----------------------------------
# Menu Rendering
# -----------------------------------
def render_menu():
    """Render the SwiftBar menu"""
    tracking_data = get_tracking_data()
    
    if not tracking_data:
        print("📦")
        print("---")
        print("No packages to track")
        print("Add tracking number | bash=/usr/bin/osascript param1=-e param2='display dialog \"Enter tracking number:\" default answer \"\" buttons {\"Cancel\",\"Add\"} default button \"Add\"' terminal=false refresh=true")
        return
    
    # Count packages by status
    status_counts = {}
    for data in tracking_data.values():
        status = data['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Create menu bar title
    total_packages = len(tracking_data)
    if status_counts.get('delivered', 0) > 0:
        title = f"📦 {total_packages} ({status_counts['delivered']} delivered)"
    elif status_counts.get('out_for_delivery', 0) > 0:
        title = f"📦 {total_packages} (🚛 {status_counts['out_for_delivery']} out for delivery)"
    elif status_counts.get('in_transit', 0) > 0:
        title = f"📦 {total_packages} (🚚 {status_counts['in_transit']} in transit)"
    else:
        title = f"📦 {total_packages}"
    
    print(title)
    print("---")
    
    # Display each package
    for tracking_number, data in tracking_data.items():
        carrier = data['carrier']
        name = data['name']
        status = data['status']
        location = data['location']
        delivery_date = data['delivery_date']
        
        # Status icon and color
        status_icon = STATUS_ICONS.get(status, '❓')
        status_color = STATUS_COLORS.get(status, 'gray')
        
        # Main package line
        package_name = name if name else f"{carrier} {tracking_number[:8]}..."
        main_line = f"{status_icon} {package_name}"
        if status_color != 'gray':
            main_line += f" | color={status_color}"
        print(main_line)
        
        # Status details
        print(f"--Status: {status.replace('_', ' ').title()}")
        if location != 'Unknown':
            print(f"--Location: {location}")
        if delivery_date != 'Unknown':
            print(f"--Delivery: {delivery_date}")
        print(f"--Tracking: {tracking_number}")
        print(f"--Carrier: {carrier}")
        
        # Open in browser option
        tracking_url = get_tracking_url(tracking_number, carrier)
        if tracking_url:
            print(f"--Open in Browser | href={tracking_url}")
        
        # Remove option
        print(f"--Remove | bash={sys.argv[0]} param1=remove param2={tracking_number} terminal=false refresh=true")
        print("---")
    
    # Management options
    print("🔄 Refresh all packages | bash={sys.argv[0]} param1=refresh terminal=true refresh=true")
    print("📋 Sync to working directory | bash=/Users/adamchiaravalle/gits/ac-swiftbar-plugins/sync-tracking-data.sh terminal=true refresh=true")
    print("Add tracking number | bash=/usr/bin/osascript param1=-e param2='display dialog \"Enter tracking number:\" default answer \"\" buttons {\"Cancel\",\"Add\"} default button \"Add\"' terminal=false refresh=true")
    print("Clear all packages | bash=/usr/bin/osascript param1=-e param2='display dialog \"Clear all tracking numbers?\" buttons {\"Cancel\",\"Clear\"} default button \"Clear\"' terminal=false refresh=true")
    print("---")
    print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# -----------------------------------
# Action Handlers
# -----------------------------------
def handle_add_tracking():
    """Handle adding a new tracking number"""
    try:
        import subprocess
        script = 'display dialog "Enter tracking number:" default answer "" buttons {"Cancel","Add"} default button "Add"'
        result = subprocess.run(['/usr/bin/osascript', '-e', script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and 'text returned:' in result.stdout:
            tracking_number = result.stdout.split('text returned:', 1)[1].strip()
            if tracking_number:
                carrier = detect_carrier(tracking_number)
                if carrier == 'Unknown':
                    print("❌ Could not detect carrier for this tracking number")
                    return
                
                # Add to tracking numbers
                tracking_numbers = load_tracking_numbers()
                
                # Check for duplicates
                if any(item['tracking_number'] == tracking_number for item in tracking_numbers):
                    print(f"⚠️ Tracking number {tracking_number} already exists")
                    return
                
                tracking_numbers.append({
                    'tracking_number': tracking_number,
                    'carrier': carrier,
                    'name': '',
                    'added': datetime.now().isoformat()
                })
                save_tracking_numbers(tracking_numbers)
                
                # Clear cache to force refresh
                if CACHE_FILE.exists():
                    CACHE_FILE.unlink()
                
                print(f"✅ Added {carrier} tracking number: {tracking_number}")
                
                # Automatically fetch initial tracking data
                print(f"🔄 Fetching initial status for {carrier} {tracking_number[:8]}...")
                data = fetch_tracking_info(tracking_number, carrier)
                if data:
                    print(f"✅ Initial status: {data['status']}")
                else:
                    print(f"⚠️ Could not fetch initial status")
    except Exception as e:
        print(f"❌ Error adding tracking number: {e}")

def handle_remove_tracking(tracking_number):
    """Handle removing a tracking number"""
    try:
        tracking_numbers = load_tracking_numbers()
        tracking_numbers = [item for item in tracking_numbers 
                          if item.get('tracking_number') != tracking_number]
        save_tracking_numbers(tracking_numbers)
        
        # Clear cache to force refresh
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        
        print(f"✅ Removed tracking number: {tracking_number}")
    except Exception as e:
        print(f"❌ Error removing tracking number: {e}")

def handle_clear_all():
    """Handle clearing all tracking numbers"""
    try:
        import subprocess
        script = 'display dialog "Clear all tracking numbers?" buttons {"Cancel","Clear"} default button "Clear"'
        result = subprocess.run(['/usr/bin/osascript', '-e', script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and 'Clear' in result.stdout:
            save_tracking_numbers([])
            
            # Clear cache
            if CACHE_FILE.exists():
                CACHE_FILE.unlink()
            
            print("✅ Cleared all tracking numbers")
    except Exception as e:
        print(f"❌ Error clearing tracking numbers: {e}")

def handle_refresh():
    """Handle manual refresh of all tracking data"""
    try:
        # Clear cache to force fresh data fetch
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        
        print("🔄 Refreshing all package data...")
        
        # Force fetch fresh data
        tracking_numbers = load_tracking_numbers()
        if not tracking_numbers:
            print("ℹ️ No packages to refresh")
            return
        
        print(f"📦 Refreshing {len(tracking_numbers)} packages...")
        
        # Fetch fresh data for all packages
        for item in tracking_numbers:
            tracking_number = item.get('tracking_number', '')
            carrier = item.get('carrier', '')
            if tracking_number and carrier:
                print(f"🔄 Fetching {carrier} {tracking_number[:8]}...")
                data = fetch_tracking_info(tracking_number, carrier)
                if data:
                    print(f"✅ {carrier} {tracking_number[:8]}... - {data['status']}")
                else:
                    print(f"⚠️ {carrier} {tracking_number[:8]}... - Failed to fetch")
        
        print("✅ Refresh complete!")
    except Exception as e:
        print(f"❌ Error during refresh: {e}")

def handle_open_browser(carrier, tracking_number):
    """Handle opening tracking page in browser"""
    try:
        tracking_url = get_tracking_url(tracking_number, carrier)
        if tracking_url:
            webbrowser.open(tracking_url)
            print(f"🌐 Opened {carrier} tracking page for {tracking_number[:8]}...")
        else:
            print(f"❌ No tracking URL available for {carrier}")
    except Exception as e:
        print(f"❌ Error opening browser: {e}")

# -----------------------------------
# Main Execution
# -----------------------------------
if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "add":
            handle_add_tracking()
        elif command == "remove" and len(sys.argv) > 2:
            handle_remove_tracking(sys.argv[2])
        elif command == "clear":
            handle_clear_all()
        elif command == "refresh":
            handle_refresh()
        elif command == "open" and len(sys.argv) > 3:
            handle_open_browser(sys.argv[2], sys.argv[3])  # carrier, tracking_number
        else:
            print("❌ Invalid command")
    else:
        # Render the menu
        render_menu()
