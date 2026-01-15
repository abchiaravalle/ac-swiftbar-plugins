#!/usr/bin/env python3
# <bitbar.title>Log</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>AC</bitbar.author>
# <bitbar.desc>Log time entries to Motion webhook with client, hours, task, and date</bitbar.desc>
# <bitbar.dependencies>python3,requests</bitbar.dependencies>

import os
import sys
import json
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from pathlib import Path

# -----------------------------------
# Configuration
# -----------------------------------
WEBHOOK_URL = "https://webhooks.usemotion.com/agent-webhook/sheet/she_48CqeEDHwLX9NgwgMjT2R1"

CLIENT_OPTIONS = [
    "Mednition",
    "P1H",
    "Kito Crosby",
    "Firebrand",
    "Indico",
    "iScope"
]

# -----------------------------------
# Helper Functions
# -----------------------------------
def get_today_date():
    """Get today's date in YYYY-MM-DD format"""
    return datetime.now().strftime("%Y-%m-%d")

def send_to_webhook(client, hours, task, date):
    """Send log entry to Motion webhook"""
    try:
        # Motion webhook expects exact column names matching the sheet
        # Try form-encoded data first (some webhooks prefer this)
        form_data = urllib.parse.urlencode({
            "Client": client,
            "# Hours": float(hours),
            "Task": task,
            "Date": date
        }).encode('utf-8')
        
        request = urllib.request.Request(
            WEBHOOK_URL,
            data=form_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'SwiftBar-Log-Plugin/1.0'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(request, timeout=10) as response:
            response_data = response.read().decode('utf-8')
            print(f"DEBUG: Sent form data: Client={client}, # Hours={hours}, Task={task}, Date={date}", file=sys.stderr)
            print(f"DEBUG: Response: {response_data[:200]}", file=sys.stderr)
            if response.status == 200:
                return True, "✅ Log entry sent successfully!"
            else:
                # If form data doesn't work, try JSON
                return send_to_webhook_json(client, hours, task, date)
    
    except urllib.error.HTTPError as e:
        # Try JSON format as fallback
        try:
            return send_to_webhook_json(client, hours, task, date)
        except:
            return False, f"❌ HTTP Error: {e.code} - {e.reason}"
    except urllib.error.URLError as e:
        return False, f"❌ Network Error: {str(e)}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def send_to_webhook_json(client, hours, task, date):
    """Send log entry to Motion webhook using JSON format"""
    # Try as a single row object first
    data = {
        "Client": client,
        "# Hours": float(hours),
        "Task": task,
        "Date": date
    }
    
    # Also try as array format (some webhooks expect this)
    # data = [data]
    
    json_data = json.dumps(data).encode('utf-8')
    
    request = urllib.request.Request(
        WEBHOOK_URL,
        data=json_data,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'SwiftBar-Log-Plugin/1.0'
        },
        method='POST'
    )
    
    with urllib.request.urlopen(request, timeout=10) as response:
        response_data = response.read().decode('utf-8')
        print(f"DEBUG: Sent JSON data: {json.dumps(data)}", file=sys.stderr)
        print(f"DEBUG: Response: {response_data[:200]}", file=sys.stderr)
        if response.status == 200:
            return True, "✅ Log entry sent successfully!"
        else:
            return False, f"❌ Error: HTTP {response.status} - {response_data[:100]}"
    
    except urllib.error.HTTPError as e:
        return False, f"❌ HTTP Error: {e.code} - {e.reason}"
    except urllib.error.URLError as e:
        return False, f"❌ Network Error: {str(e)}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def show_client_picker():
    """Show client selection dialog"""
    client_options_str = '", "'.join(CLIENT_OPTIONS)
    
    script = f'''
    set clientOptions to {{"{client_options_str}"}}
    choose from list clientOptions with prompt "Select Client:" default items {{item 1 of clientOptions}}
    if result is false then
        return ""
    else
        return item 1 of result
    end if
    '''
    
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None

def show_input_dialog(prompt, default=""):
    """Show input dialog and return user input"""
    script = f'''
    display dialog "{prompt}" default answer "{default}" buttons {{"Cancel", "OK"}} default button "OK"
    if button returned of result is "OK" then
        return text returned of result
    else
        return ""
    end if
    '''
    
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None

def handle_log_entry(client=None):
    """Handle the log entry process"""
    # Get client if not provided
    if not client:
        client = show_client_picker()
        if not client:
            print("❌ Cancelled: No client selected")
            return
    
    # Get hours
    hours = show_input_dialog("Enter Hours:", "0.0")
    if not hours:
        print("❌ Cancelled: No hours entered")
        return
    
    try:
        float(hours)  # Validate it's a number
    except ValueError:
        print(f"❌ Error: '{hours}' is not a valid number")
        return
    
    # Get task
    task = show_input_dialog("Enter Task Description:", "")
    if not task:
        print("❌ Cancelled: No task entered")
        return
    
    # Get date (default to today)
    date = show_input_dialog("Enter Date (YYYY-MM-DD):", get_today_date())
    if not date:
        print("❌ Cancelled: No date entered")
        return
    
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Error: '{date}' is not a valid date (use YYYY-MM-DD)")
        return
    
    # Send to webhook
    success, message = send_to_webhook(client, hours, task, date)
    print(message)

def render_menu():
    """Render the SwiftBar menu"""
    print("📝 Log")
    print("---")
    print("➕ New Log Entry")
    for client in CLIENT_OPTIONS:
        # URL encode the client name for the parameter
        client_encoded = urllib.parse.quote(client)
        print(f"  └─ {client} | bash={sys.argv[0]} param1=log param2={client_encoded} terminal=true refresh=true")
    print("---")
    print("ℹ️ Webhook: Motion Sheet")

# -----------------------------------
# Main Execution
# -----------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "log":
            client = None
            if len(sys.argv) > 2:
                # Decode the client name from URL encoding
                client = urllib.parse.unquote(sys.argv[2])
            handle_log_entry(client)
        else:
            render_menu()
    else:
        render_menu()

