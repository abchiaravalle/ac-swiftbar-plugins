#!/usr/bin/env python3
# <bitbar.title>WP Engine Dynamic Installs + Actions + SSH</bitbar.title>
# <bitbar.version>v1.1</bitbar.version>
# <bitbar.author>You</bitbar.author>
# <bitbar.desc>Fetch WP Engine installs from the API, run safe actions, and open SSH. No PATCH or DELETE.</bitbar.desc>
# <bitbar.dependencies>python3</bitbar.dependencies>

import os
import sys
import time
import json
from pathlib import Path
from typing import Optional

# -----------------------------------
# .env file loading
# -----------------------------------
def load_env_file():
    """Load environment variables from .env file in the same directory as the script."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print(f"DEBUG: Loading .env file from {env_file}", file=sys.stderr)
        with open(env_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    os.environ[key.strip()] = value
                    print(f"DEBUG: Loaded {key.strip()}={'SET' if value else 'EMPTY'}", file=sys.stderr)
    else:
        print(f"DEBUG: No .env file found at {env_file}", file=sys.stderr)

# Load .env file before setting up environment variables
load_env_file()

# -----------------------------------
# Env config
# -----------------------------------
# -----------------------------------
# Environment configuration (loaded from .env file)
# -----------------------------------
GLOBAL_BEARER = os.getenv("GLOBAL_BEARER", "").strip()
WPE_API_USER  = os.getenv("WPE_API_USER", "").strip()
WPE_API_PASS  = os.getenv("WPE_API_PASS", "").strip()

# Multiple WP Engine accounts (up to 5)
WPE_API_USER1 = os.getenv("WPE_API_USER1", "").strip()
WPE_API_PASS1 = os.getenv("WPE_API_PASS1", "").strip()
WPE_API_USER2 = os.getenv("WPE_API_USER2", "").strip()
WPE_API_PASS2 = os.getenv("WPE_API_PASS2", "").strip()
WPE_API_USER3 = os.getenv("WPE_API_USER3", "").strip()
WPE_API_PASS3 = os.getenv("WPE_API_PASS3", "").strip()
WPE_API_USER4 = os.getenv("WPE_API_USER4", "").strip()
WPE_API_PASS4 = os.getenv("WPE_API_PASS4", "").strip()
WPE_API_USER5 = os.getenv("WPE_API_USER5", "").strip()
WPE_API_PASS5 = os.getenv("WPE_API_PASS5", "").strip()

WPE_SSH_KEY   = os.getenv("WPE_SSH_KEY", "").strip()
REFRESH_SECS  = int(os.getenv("REFRESH_SECS", "300"))
API_BASE      = os.getenv("WPE_API_BASE", "https://api.wpengineapi.com").rstrip("/")
BACKUP_EMAILS = os.getenv("WPE_BACKUP_EMAILS", "").strip()
BACKUP_DESC_TEMPLATE = os.getenv("WPE_BACKUP_DESC", "Backup from SwiftBar - {datetime}")
MAINWP_LABEL = os.getenv("MAINWP_LABEL", "").strip()
MAINWP_URL = os.getenv("MAINWP_URL", "").strip()
MAX_INSTALLS = int(os.getenv("WPE_MAX_INSTALLS", "100"))  # Limit to prevent agency account overload
V1            = f"{API_BASE}/v1"
INST_LIST_URL = f"{V1}/installs"   # GET list, POST create   [oai_citation:1‡Postman](https://www.postman.com/tom-griffin/wp-engine-api/folder/7kc1omz/installs)

# optional override for slug field
SLUG_FIELD    = os.getenv("WPE_SLUG_FIELD", "").strip()

# -----------------------------------
# Cache
# -----------------------------------
CACHE_DIR  = Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache")))
CACHE_FILE = CACHE_DIR / "swiftbar_wpe_dynamic_cache.json"

def load_cache():
    try:
        if CACHE_FILE.exists():
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            print(f"DEBUG: Loaded cache with {len(cache.get('installs', []))} installs", file=sys.stderr)
            return cache
    except Exception as e:
        print(f"DEBUG: Error loading cache: {e}", file=sys.stderr)
        pass
    print(f"DEBUG: No cache file found, returning empty cache", file=sys.stderr)
    return {"installs": [], "fetched_at": 0, "backup_ids": {}, "accounts_used": []}

def save_cache(cache):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass

# -----------------------------------
# HTTP helpers
# -----------------------------------
def get_configured_accounts():
    """Get all configured WP Engine accounts."""
    accounts = []

    # Legacy single account
    if WPE_API_USER and WPE_API_PASS:
        accounts.append({"user": WPE_API_USER, "pass": WPE_API_PASS, "name": "legacy"})

    # Multiple accounts
    account_pairs = [
        (WPE_API_USER1, WPE_API_PASS1, "account1"),
        (WPE_API_USER2, WPE_API_PASS2, "account2"),
        (WPE_API_USER3, WPE_API_PASS3, "account3"),
        (WPE_API_USER4, WPE_API_PASS4, "account4"),
        (WPE_API_USER5, WPE_API_PASS5, "account5"),
    ]

    for user, password, name in account_pairs:
        if user and password:
            accounts.append({"user": user, "pass": password, "name": name})

    return accounts

def add_auth(headers: dict, account: dict = None) -> dict:
    headers = dict(headers or {})

    if GLOBAL_BEARER:
        headers["Authorization"] = f"Bearer {GLOBAL_BEARER[:10]}..."
        print(f"DEBUG AUTH: Using Bearer token", file=sys.stderr)
        return headers

    if account:
        import base64
        token = base64.b64encode(f"{account['user']}:{account['pass']}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
        print(f"DEBUG AUTH: Using Basic auth for {account['name']} (user: {account['user']})", file=sys.stderr)
        return headers

    # Fallback to legacy credentials
    if WPE_API_USER and WPE_API_PASS:
        import base64
        token = base64.b64encode(f"{WPE_API_USER}:{WPE_API_PASS}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
        print(f"DEBUG AUTH: Using legacy Basic auth for user: {WPE_API_USER}", file=sys.stderr)
        return headers

    print(f"DEBUG AUTH: No authentication credentials found!", file=sys.stderr)
    return headers

def http_request(method: str, url: str, body: Optional[dict] = None, timeout=30, account: dict = None):
    import urllib.request, urllib.error
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    print(f"DEBUG API: {method} {url}", file=sys.stderr)
    print(f"DEBUG API: Headers before auth: {headers}", file=sys.stderr)
    if body is not None:
        print(f"DEBUG API: Body: {json.dumps(body)}", file=sys.stderr)

    authenticated_headers = add_auth(headers, account)
    print(f"DEBUG API: Headers after auth: {authenticated_headers}", file=sys.stderr)
    req = urllib.request.Request(url=url, method=method.upper(), headers=authenticated_headers, data=data)
    try:
        print(f"DEBUG API: Opening connection to URL...", file=sys.stderr)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            print(f"DEBUG API: Connection successful, response code: {resp.getcode()}", file=sys.stderr)
            raw = resp.read()
            print(f"DEBUG API: Response body length: {len(raw)} bytes", file=sys.stderr)
            ctype = resp.headers.get("Content-Type", "")
            print(f"DEBUG API: Content-Type: {ctype}", file=sys.stderr)
            parsed = None
            # Handle successful responses with empty bodies (like HTTP 202 Accepted)
            if len(raw.strip()) == 0 and 200 <= resp.getcode() < 300:
                parsed = {"status": "success", "message": "Request accepted"}
            elif "application/json" in ctype or raw.strip().startswith((b"{", b"[")):
                parsed = json.loads(raw.decode("utf-8", errors="replace"))
            else:
                parsed = {"_raw": raw.decode("utf-8", errors="replace")}
            return resp.getcode(), parsed
    except urllib.error.HTTPError as e:
        print(f"DEBUG API: HTTPError {e.code}: {e.reason}", file=sys.stderr)
        try:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"DEBUG API: Error response body: {err_body}", file=sys.stderr)
            try:
                parsed_error = json.loads(err_body)
                return e.code, parsed_error
            except json.JSONDecodeError:
                return e.code, {"error": err_body}
        except Exception as read_error:
            print(f"DEBUG API: Could not read error body: {read_error}", file=sys.stderr)
            return e.code, {"error": str(e)}
    except urllib.error.URLError as e:
        print(f"DEBUG API: URLError: {e.reason}", file=sys.stderr)
        return 0, {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        print(f"DEBUG API: Unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
        return 0, {"error": f"Unexpected error: {type(e).__name__}: {e}"}

def api_get(url, account=None):  return http_request("GET", url, account=account)
def api_post(url, body=None, account=None): return http_request("POST", url, body or {}, account=account)

# -----------------------------------
# Install parsing
# -----------------------------------
def extract_installs(payload):
    """
    Return list of dicts: [{"id": "<uuid>", "name": "...", "slug": "envslug"}]
    Field names vary across accounts, so we probe common shapes.
    """
    print(f"DEBUG: extract_installs received payload type: {type(payload)}", file=sys.stderr)
    if isinstance(payload, dict):
        print(f"DEBUG: payload keys: {list(payload.keys())}", file=sys.stderr)
    elif isinstance(payload, list):
        print(f"DEBUG: payload is list with {len(payload)} items", file=sys.stderr)

    items = []
    data = payload
    if isinstance(data, dict):
        print(f"DEBUG: Looking for data array in keys: {list(data.keys())}", file=sys.stderr)
        for key in ["installs", "results", "data"]:
            if key in data and isinstance(data[key], list):
                print(f"DEBUG: Found data array in key '{key}' with {len(data[key])} items", file=sys.stderr)
                data = data[key]
                break
        if isinstance(data, dict):
            print(f"DEBUG: Converting dict values to list", file=sys.stderr)
            data = list(data.values())

    if not isinstance(data, list):
        print(f"DEBUG: Final data is not a list, type: {type(data)}", file=sys.stderr)
        return items

    print(f"DEBUG: Processing {len(data)} items from data list", file=sys.stderr)

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue

        # Show first few items for debugging grouping
        if i < 3:
            print(f"DEBUG INSTALL {i}: Available fields: {list(item.keys())}", file=sys.stderr)
            print(f"DEBUG INSTALL {i}: Full data: {json.dumps(item, indent=2)}", file=sys.stderr)

        # id candidates
        iid = item.get("id") or item.get("install_id") or item.get("uuid") or ""
        # display name
        name = item.get("name") or item.get("site_name") or item.get("display_name") or item.get("environment") or item.get("slug") or "install"
        # slug candidates
        slug = ""
        if SLUG_FIELD:
            slug = str(item.get(SLUG_FIELD, "")).strip()
        for k in ["environment", "slug", "name", "system_name", "install_name"]:
            if not slug and item.get(k):
                slug = str(item[k]).strip()
        if slug:
            items.append({"id": str(iid), "name": name, "slug": slug})
    return items

# -----------------------------------
# SSH
# -----------------------------------
def ssh_command_for(env_name: str) -> str:
    """Generate SSH command for WP Engine environment using the actual environment name (not slug)."""
    host = f"{env_name}.ssh.wpengine.net"
    user = env_name

    if WPE_SSH_KEY:
        return f"ssh -i {WPE_SSH_KEY} -o IdentitiesOnly=yes {user}@{host}"
    return f"ssh {user}@{host}"

def do_open_terminal(env_name: str, app: str = "Terminal"):
    ssh_cmd = ssh_command_for(env_name)
    try:
        import subprocess
        if app.lower() == "iterm2":
            osa = [
                "/usr/bin/osascript",
                "-e", 'tell application "iTerm" to activate',
                "-e", 'tell application "iTerm" to create window with default profile',
                "-e", f'tell application "iTerm" to tell current session of current window to write text "{ssh_cmd}"'
            ]
        else:
            osa = [
                "/usr/bin/osascript",
                "-e", f'tell application "Terminal" to do script "{ssh_cmd}"',
                "-e", 'tell application "Terminal" to activate'
            ]
        subprocess.Popen(osa)
    except Exception:
        pass

# -----------------------------------
# Small UI helpers
# -----------------------------------
def plugin_path():
    return os.getenv("SWIFTBAR_PLUGIN_PATH", sys.argv[0])

def osascript_prompt(prompt_text: str, default_text: str = "") -> Optional[str]:
    """
    Show a macOS prompt and return entered text or None if canceled.
    """
    try:
        import subprocess, shlex
        script = f'display dialog "{prompt_text}" default answer "{default_text}" buttons {{"Cancel","OK"}} default button "OK"'
        proc = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True, text=True
        )
        # when canceled, AppleScript returns nonzero
        if proc.returncode != 0:
            return None
        out = proc.stdout or ""
        # format is like: button returned:OK, text returned:whatever
        if "text returned:" in out:
            return out.split("text returned:", 1)[1].strip()
        return None
    except Exception:
        return None

def notify(title: str, message: str):
    try:
        import subprocess
        osa = f'display notification "{message}" with title "{title}"'
        subprocess.Popen(["/usr/bin/osascript", "-e", osa])
    except Exception:
        pass

# -----------------------------------
# Actions - API wrappers
# Reference of available endpoints and methods pulled from public Postman workspace:
# - /v1/installs: GET list, POST create
# - /v1/installs/{id}: GET details
# - /v1/installs/{id}/purge_cache: POST purge
# - /v1/installs/{id}/backups: POST request backup, GET status via /backups/{backup_id}
# - /v1/installs/{id}/domains: GET list, POST add
# - /v1/installs/{id}/domains/bulk: POST add multiple
# - /v1/installs/{id}/domains/{domain_id}/check_status: POST check
# Excluding PATCH and DELETE routes on purpose.   [oai_citation:2‡Postman](https://www.postman.com/tom-griffin/wp-engine-api/folder/7kc1omz/installs)
# -----------------------------------
def get_install_by_id(install_id: str):
    return api_get(f"{V1}/installs/{install_id}")

def purge_cache(install_id: str, account: dict = None):
    print(f"DEBUG: Attempting cache purge for install_id: {install_id}", file=sys.stderr)
    body = {"type": "all"}  # Required parameter based on API error
    return api_post(f"{V1}/installs/{install_id}/purge_cache", body, account=account)

def request_backup(install_id: str, label: Optional[str] = None, account: dict = None):
    # Both description and notification_emails are required
    emails = [email.strip() for email in BACKUP_EMAILS.split(",") if email.strip()] if BACKUP_EMAILS else []

    # Generate description with date/time template
    if label:
        description = label
    else:
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        description = BACKUP_DESC_TEMPLATE.format(datetime=current_time)

    body = {
        "description": description,
        "notification_emails": emails
    }
    print(f"DEBUG: Requesting backup for install_id: {install_id}, body: {body}", file=sys.stderr)
    return api_post(f"{V1}/installs/{install_id}/backups", body, account=account)

def poll_backup_status(install_id: str, backup_id: str, poll_interval: int = 30, account: dict = None):
    """Poll backup status every poll_interval seconds until completion."""
    import time

    print(f"🔄 Polling backup status every {poll_interval} seconds...")
    print(f"📋 Backup ID: {backup_id}")
    print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    completed_states = ['completed', 'success', 'finished', 'done']
    failed_states = ['failed', 'error', 'cancelled', 'canceled', 'aborted']
    in_progress_states = ['requested', 'pending', 'running', 'in_progress', 'processing', 'queued']

    poll_count = 0
    start_time = time.time()

    while True:
        poll_count += 1
        elapsed_time = int(time.time() - start_time)

        print(f"\n[Poll #{poll_count}] Checking status... (elapsed: {elapsed_time}s)")

        code, data = get_backup_status(install_id, backup_id, account)

        if not (code and 200 <= code < 300):
            print(f"❌ Failed to get backup status - HTTP {code}")
            if data:
                print(f"Error: {data}")
            break

        status = "unknown"
        progress = None

        if isinstance(data, dict):
            print(f"DEBUG POLL: Full response data: {json.dumps(data, indent=2)}", file=sys.stderr)
            raw_status = data.get("status", "unknown")
            status = raw_status.lower() if raw_status else "unknown"
            progress = data.get("progress") or data.get("percentage")

            print(f"DEBUG POLL: Raw status from API: '{raw_status}'", file=sys.stderr)
            print(f"DEBUG POLL: Processed status: '{status}'", file=sys.stderr)
            print(f"📊 Status: {status}")
            if progress:
                print(f"📈 Progress: {progress}%")

            # Check for completion (exact match)
            if status in completed_states:
                print(f"✅ Backup completed successfully!")
                print(f"⏱️  Total time: {elapsed_time} seconds")
                notify("Backup Complete", f"Backup {backup_id[:8]}... completed successfully")
                break

            # Check for failure (exact match)
            if status in failed_states:
                print(f"❌ Backup failed with status: {status}")
                print(f"⏱️  Failed after: {elapsed_time} seconds")
                notify("Backup Failed", f"Backup {backup_id[:8]}... failed")
                break

            # Check for known in-progress states
            if status in in_progress_states:
                print(f"⏳ Backup in progress (status: {status})...")
            else:
                print(f"⏳ Backup status: {status} (continuing to poll)...")

        else:
            print(f"⚠️  Unexpected response format: {data}")

        # Wait before next poll
        if not (status in completed_states or status in failed_states):
            print(f"💤 Waiting {poll_interval} seconds before next check...")
            time.sleep(poll_interval)

        # Safety check - don't poll forever (max 30 minutes)
        if elapsed_time > 1800:
            print(f"⏰ Polling timeout after 30 minutes")
            notify("Backup Polling Timeout", f"Stopped polling backup {backup_id[:8]}... after 30 minutes")
            break

def get_backup_status(install_id: str, backup_id: str, account: dict = None):
    return api_get(f"{V1}/installs/{install_id}/backups/{backup_id}", account=account)

def find_account_for_install(install_id: str):
    """Find which account an install belongs to by trying each account."""
    configured_accounts = get_configured_accounts()

    for account in configured_accounts:
        print(f"DEBUG: Checking if install {install_id} belongs to {account['name']}", file=sys.stderr)
        code, data = api_get(f"{V1}/installs/{install_id}", account=account)
        if code and 200 <= code < 300:
            print(f"DEBUG: Install {install_id} found in {account['name']}", file=sys.stderr)
            return account

    print(f"DEBUG: Install {install_id} not found in any account, using first available", file=sys.stderr)
    return configured_accounts[0] if configured_accounts else None

def list_backups(install_id: str, account: dict = None):
    return api_get(f"{V1}/installs/{install_id}/backups", account=account)

def test_cache_purge_endpoints(install_id: str):
    """Test different cache purge endpoint variations to find the correct one."""
    endpoints_to_try = [
        f"{V1}/installs/{install_id}/purge_cache",
        f"{V1}/installs/{install_id}/cache/purge",
        f"{V1}/installs/{install_id}/purge-cache",
        f"{V1}/installs/{install_id}/cache_purge",
        f"{V1}/installs/{install_id}/clear-cache",
    ]

    print(f"DEBUG: Testing cache purge endpoints for install_id: {install_id}", file=sys.stderr)

    for endpoint in endpoints_to_try:
        print(f"DEBUG: Trying endpoint: {endpoint}", file=sys.stderr)
        code, data = api_post(endpoint, {"type": "all"})
        print(f"DEBUG: Response code: {code}", file=sys.stderr)
        if code and 200 <= code < 300:
            print(f"DEBUG: SUCCESS! Working endpoint: {endpoint}", file=sys.stderr)
            return code, data, endpoint
        elif code == 400:
            print(f"DEBUG: 400 Bad Request for: {endpoint}", file=sys.stderr)
            if data:
                print(f"DEBUG: Error response: {json.dumps(data, indent=2)}", file=sys.stderr)
        elif code == 404:
            print(f"DEBUG: 404 Not Found for: {endpoint}", file=sys.stderr)
        else:
            print(f"DEBUG: Unexpected response code {code} for: {endpoint}", file=sys.stderr)

    return None, None, None

def test_backup_endpoints(install_id: str, description: str = ""):
    """Test different backup endpoint variations to find the correct one."""
    emails = [email.strip() for email in BACKUP_EMAILS.split(",") if email.strip()] if BACKUP_EMAILS else []
    bodies_to_try = [
        {"description": description or "Backup created via API", "notification_emails": emails},
        {"description": description or "Backup created via API", "notification_emails": []},
        {"label": description or "Backup created via API", "notification_emails": emails},
        {"name": description or "Backup created via API", "notification_emails": emails},
    ]

    endpoint = f"{V1}/installs/{install_id}/backups"

    print(f"DEBUG: Testing backup request bodies for install_id: {install_id}", file=sys.stderr)

    for i, body in enumerate(bodies_to_try):
        print(f"DEBUG: Trying body variation {i+1}: {json.dumps(body)}", file=sys.stderr)
        code, data = api_post(endpoint, body)
        print(f"DEBUG: Response code: {code}", file=sys.stderr)
        if code and 200 <= code < 300:
            print(f"DEBUG: SUCCESS! Working body format: {json.dumps(body)}", file=sys.stderr)
            return code, data, body
        elif code == 400:
            print(f"DEBUG: 400 Bad Request for body: {json.dumps(body)}", file=sys.stderr)
            if data:
                print(f"DEBUG: Error response: {json.dumps(data, indent=2)}", file=sys.stderr)
        else:
            print(f"DEBUG: Unexpected response code {code} for body: {json.dumps(body)}", file=sys.stderr)

    return None, None, None

def list_domains(install_id: str):
    return api_get(f"{V1}/installs/{install_id}/domains")

# -----------------------------------
# SwiftBar rendering
# -----------------------------------



def render_installs_grouped_by_site(installs):
    # Sort all installs alphabetically by name
    sorted_installs = sorted(installs, key=lambda x: x.get('name', '').lower())

    # Render each install at top level
    for inst in sorted_installs:
        name = inst.get("name", "install")
        slug = inst.get("slug", "")
        iid = inst.get("id", "")
        label = f"{name} ({slug})" if slug else name
        print(f"{label}")
        # SSH options
        print(f"--Open SSH in Terminal | bash={plugin_path()} param1=ssh_term param2={name} terminal=false")
        print(f"--Open SSH in iTerm2 | bash={plugin_path()} param1=ssh_iterm param2={name} terminal=false")
        print(f"--Show SSH command | bash=/bin/echo param1='{ssh_command_for(name).replace('|','¦')}' terminal=true")
        # API actions - only GET or POST
        if iid:
            print(f"--Purge cache | bash={plugin_path()} param1=purge_cache param2={iid} terminal=true")
            print(f"--Request backup | bash={plugin_path()} param1=backup_request param2={iid} terminal=true")
            print(f"--Check backup status... | bash={plugin_path()} param1=backup_status_prompt param2={iid} terminal=false")
            print(f"--Check latest backup | bash={plugin_path()} param1=latest_backup_status param2={iid} terminal=false")
            print(f"--Get install details | bash={plugin_path()} param1=install_details param2={iid} terminal=true")
            print(f"--Domains")
            print(f"----List domains | bash={plugin_path()} param1=domains_list param2={iid} terminal=true")

def render_title(cache):
    count = len(cache.get("installs", []))
    print(f"DEBUG: render_title called with {count} installs in cache", file=sys.stderr)
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wpe-icon.png")
    print(f"{count} | image={icon_path}")

def render_menu():
    cache = load_cache()
    print(f"DEBUG: render_menu called, cache has {len(cache.get('installs', []))} installs", file=sys.stderr)
    render_title(cache)
    print("---")

    # Add MainWP link if configured
    if MAINWP_LABEL and MAINWP_URL:
        print(f"{MAINWP_LABEL} | href={MAINWP_URL}")
        print("---")

    print(f"Refresh installs now | bash={plugin_path()} param1=refresh terminal=false refresh=true")
    print(f"Cache file: {CACHE_FILE}")
    print("---")
    if cache.get("installs"):
        print(f"DEBUG: About to render {len(cache['installs'])} installs", file=sys.stderr)
        render_installs_grouped_by_site(cache["installs"])
    else:
        print(f"DEBUG: No installs in cache to render", file=sys.stderr)
        print("[No installs yet]")
        print(f"--Run refresh | bash={plugin_path()} param1=refresh terminal=false refresh=true")
    print("---")
    print(f"Auto refresh every {REFRESH_SECS}s. Change with REFRESH_SECS env.")

# -----------------------------------
# Data refresh
# -----------------------------------
def do_refresh_installs():
    cache = load_cache()
    all_installs = []
    accounts_used = []

    # Get all configured accounts
    configured_accounts = get_configured_accounts()

    print(f"DEBUG: WPE_API_USER: '{WPE_API_USER}' (empty: {not WPE_API_USER})", file=sys.stderr)
    print(f"DEBUG: WPE_API_PASS: {'SET' if WPE_API_PASS else 'EMPTY'}", file=sys.stderr)

    if not configured_accounts:
        print("DEBUG: No WP Engine accounts configured!", file=sys.stderr)
        cache["installs"] = []
        cache["fetched_at"] = int(time.time())
        cache["accounts_used"] = []
        save_cache(cache)
        return

    print(f"DEBUG: Found {len(configured_accounts)} configured accounts", file=sys.stderr)
    for account in configured_accounts:
        print(f"DEBUG: Account {account['name']}: user='{account['user']}', pass={'SET' if account['pass'] else 'EMPTY'}", file=sys.stderr)

    # Fetch installs from each account
    for account in configured_accounts:
        print(f"DEBUG: Fetching installs from {account['name']} (user: {account['user']})", file=sys.stderr)
        account_installs = fetch_installs_from_account(account)

        if account_installs:
            print(f"DEBUG: Got {len(account_installs)} installs from {account['name']}", file=sys.stderr)
            all_installs.extend(account_installs)
            accounts_used.append(account['name'])
        else:
            print(f"DEBUG: No installs from {account['name']}", file=sys.stderr)

    print(f"DEBUG: Final total installs before dedup: {len(all_installs)}", file=sys.stderr)

    if all_installs:
        print(f"DEBUG: Starting deduplication with {len(all_installs)} installs", file=sys.stderr)
        # dedupe by install ID instead of slug (slug is environment type, not unique)
        seen = set()
        uniq = []
        for i in all_installs:
            install_id = i.get("id", "")
            name = i.get("name", "")
            slug = i.get("slug", "")
            print(f"DEBUG: Processing install: name='{name}', slug='{slug}', id='{install_id}'", file=sys.stderr)
            if install_id and install_id not in seen:
                uniq.append(i)
                seen.add(install_id)
                print(f"DEBUG: Added install with ID '{install_id}' (total unique: {len(uniq)})", file=sys.stderr)
            else:
                print(f"DEBUG: Skipping install - id='{install_id}' (empty={not install_id}, duplicate={install_id in seen})", file=sys.stderr)

        print(f"DEBUG: After deduplication: {len(uniq)} unique installs", file=sys.stderr)
        cache["installs"] = uniq
        cache["fetched_at"] = int(time.time())
        cache["accounts_used"] = accounts_used
        save_cache(cache)
        print(f"DEBUG: Saved {len(uniq)} installs from {len(accounts_used)} accounts to cache", file=sys.stderr)
    else:
        # keep old cache
        pass

def fetch_installs_from_account(account):
    """Fetch all installs from a single WP Engine account."""
    print(f"DEBUG: Starting install fetch from {INST_LIST_URL} for {account['name']}", file=sys.stderr)

    # First try without pagination to get all results
    code, payload = api_get(INST_LIST_URL, account=account)
    print(f"DEBUG: Non-paginated response code: {code}", file=sys.stderr)

    if not (code and 200 <= code < 300):
        print(f"DEBUG: Failed to fetch installs from {account['name']}", file=sys.stderr)
        return []

    installs = extract_installs(payload)
    print(f"DEBUG: Extracted {len(installs)} installs from {account['name']} (non-paginated)", file=sys.stderr)

    # If we got a reasonable number of installs, return them
    if installs and len(installs) < 500:  # Sanity check
        return installs

    # If we got too many or none, try paginated approach with strict duplicate detection
    all_installs = []
    seen_ids = set()
    page = 1
    per_page = 50
    consecutive_duplicate_pages = 0

    print(f"DEBUG: Falling back to paginated fetch for {account['name']}", file=sys.stderr)

    while True:
        url_with_pagination = f"{INST_LIST_URL}?page={page}&per_page={per_page}"
        print(f"DEBUG: Fetching page {page} for {account['name']}: {url_with_pagination}", file=sys.stderr)
        code, payload = api_get(url_with_pagination, account=account)

        if not (code and 200 <= code < 300):
            print(f"DEBUG: Pagination failed at page {page} for {account['name']}", file=sys.stderr)
            break

        current_installs = extract_installs(payload)
        print(f"DEBUG: Extracted {len(current_installs)} installs from page {page} of {account['name']}", file=sys.stderr)

        if not current_installs:
            print(f"DEBUG: No results on page {page}, stopping", file=sys.stderr)
            break

        # Check for new unique installs
        new_installs = []
        for install in current_installs:
            install_id = install.get("id", "")
            if install_id and install_id not in seen_ids:
                seen_ids.add(install_id)
                new_installs.append(install)

        if not new_installs:
            consecutive_duplicate_pages += 1
            print(f"DEBUG: No new installs on page {page}, consecutive duplicate pages: {consecutive_duplicate_pages}", file=sys.stderr)
            if consecutive_duplicate_pages >= 2:  # Stop after 2 consecutive pages with no new data
                print(f"DEBUG: Stopping pagination due to repeated duplicate results", file=sys.stderr)
                break
        else:
            consecutive_duplicate_pages = 0
            all_installs.extend(new_installs)
            print(f"DEBUG: Added {len(new_installs)} new installs, total: {len(all_installs)}", file=sys.stderr)

        # Safety checks
        if len(all_installs) >= 200:  # Reasonable limit
            print(f"DEBUG: Hit safety limit of 200 installs for {account['name']}", file=sys.stderr)
            break

        if page >= 5:  # Don't fetch more than 5 pages
            print(f"DEBUG: Hit page limit of 5 for {account['name']}", file=sys.stderr)
            break

        page += 1

    return all_installs

# -----------------------------------
# Action runners
# -----------------------------------
def run_purge_cache(iid: str):
    # Find which account this install belongs to
    account = find_account_for_install(iid)
    # First try the standard endpoint
    code, data = purge_cache(iid, account)

    if code and (200 <= code < 300 or code == 202):
        if code == 202:
            success_msg = "Cache purge accepted and initiated successfully (HTTP 202)"
        else:
            success_msg = "Cache purge initiated successfully"
            if isinstance(data, dict) and "status" in data:
                success_msg += f" - Status: {data['status']}"
        notify("Cache Purged", success_msg)
        print(f"✅ {success_msg}")
        print(json.dumps(data, indent=2))
    elif code == 400:
        # If we get a 400 error, test different endpoint variations
        print(f"❌ Standard cache purge failed with 400 error, testing alternatives...", file=sys.stderr)
        test_code, test_data, working_endpoint = test_cache_purge_endpoints(iid)

        if test_code and 200 <= test_code < 300:
            success_msg = f"Cache purge successful using: {working_endpoint}"
            notify("Cache Purged", success_msg)
            print(f"✅ {success_msg}")
            print(json.dumps(test_data, indent=2))
        else:
            error_msg = f"All cache purge endpoints failed - original HTTP {code}"
            notify("Cache Purge Failed", error_msg)
            print(f"❌ {error_msg}")
            print(json.dumps(data, indent=2))
    else:
        error_msg = f"Cache purge failed - HTTP {code}"
        notify("Cache Purge Failed", error_msg)
        print(f"❌ {error_msg}")
        print(json.dumps(data, indent=2))

def run_backup_request(iid: str):
    label = osascript_prompt("Optional backup description", "")
    # Find which account this install belongs to
    account = find_account_for_install(iid)
    code, data = request_backup(iid, label, account)

    if code and (200 <= code < 300 or code == 202):
        # Extract and cache the backup ID
        backup_id = None
        if isinstance(data, dict):
            backup_id = data.get("id") or data.get("backup_id") or data.get("uuid")

        if code == 202:
            success_msg = "Backup request accepted and initiated successfully (HTTP 202)"
            if backup_id:
                success_msg += f" - ID: {backup_id}"
                # Cache the backup ID for this install
                cache = load_cache()
                if "backup_ids" not in cache:
                    cache["backup_ids"] = {}
                cache["backup_ids"][iid] = str(backup_id)
                save_cache(cache)

                notify("Backup Initiated", success_msg)
                print(f"✅ {success_msg}")

                # Start polling for completion
                print(f"\n" + "="*60)
                print(f"🚀 Starting automatic status polling...")
                poll_backup_status(iid, backup_id, account=account)

            else:
                notify("Backup Initiated", success_msg)
                print(f"✅ {success_msg}")
                print("ℹ️  No backup ID returned - cannot poll status automatically")
        elif backup_id:
            # Cache the backup ID for this install
            cache = load_cache()
            if "backup_ids" not in cache:
                cache["backup_ids"] = {}
            cache["backup_ids"][iid] = str(backup_id)
            save_cache(cache)

            success_msg = f"Backup created successfully - ID: {backup_id}"
            notify("Backup Created", success_msg)
            print(f"✅ {success_msg}")

            # Start polling for completion
            print(f"\n" + "="*60)
            print(f"🚀 Starting automatic status polling...")
            poll_backup_status(iid, backup_id, account=account)

        else:
            success_msg = "Backup request submitted successfully"
            notify("Backup Requested", success_msg)
            print(f"✅ {success_msg}")
    elif code == 400:
        # If we get a 400 error, test different body formats
        print(f"❌ Standard backup request failed with 400 error, testing alternatives...", file=sys.stderr)
        test_code, test_data, working_body = test_backup_endpoints(iid, label or "")

        if test_code and 200 <= test_code < 300:
            # Extract and cache backup ID from successful test
            backup_id = None
            if isinstance(test_data, dict):
                backup_id = test_data.get("id") or test_data.get("backup_id") or test_data.get("uuid")

            if backup_id:
                cache = load_cache()
                if "backup_ids" not in cache:
                    cache["backup_ids"] = {}
                cache["backup_ids"][iid] = str(backup_id)
                save_cache(cache)

            success_msg = f"Backup created successfully using body: {json.dumps(working_body)}"
            notify("Backup Created", success_msg)
            print(f"✅ {success_msg}")

            # Start polling for completion if we have a backup ID
            if backup_id:
                print(f"\n" + "="*60)
                print(f"🚀 Starting automatic status polling...")
                poll_backup_status(iid, backup_id, account=account)
        else:
            error_msg = f"All backup request formats failed - original HTTP {code}"
            notify("Backup Failed", error_msg)
            print(f"❌ {error_msg}")
    else:
        error_msg = f"Backup request failed - HTTP {code}"
        notify("Backup Failed", error_msg)
        print(f"❌ {error_msg}")

def run_backup_status_prompt(iid: str):
    # Try to get cached backup ID first
    cache = load_cache()
    cached_backup_id = cache.get("backup_ids", {}).get(iid, "")

    default_text = cached_backup_id if cached_backup_id else ""
    prompt_text = "Enter backup_id to check"
    if cached_backup_id:
        prompt_text += f" (or use cached: {cached_backup_id[:8]}...)"

    bkid = osascript_prompt(prompt_text, default_text)
    if not bkid:
        return

    # Find which account this install belongs to
    account = find_account_for_install(iid)
    code, data = get_backup_status(iid, bkid, account)

    if code and 200 <= code < 300:
        status_info = "Backup status retrieved"
        if isinstance(data, dict) and "status" in data:
            status_info += f" - Status: {data['status']}"
        notify("Backup Status", status_info)
        print(f"📋 {status_info}")
        print(json.dumps(data, indent=2))
    else:
        error_msg = f"Failed to get backup status - HTTP {code}"
        notify("Backup Status Failed", error_msg)
        print(f"❌ {error_msg}")
        print(json.dumps(data, indent=2))

def run_latest_backup_status(iid: str):
    # Find which account this install belongs to
    account = find_account_for_install(iid)

    # Get list of backups for this install
    code, data = list_backups(iid, account)

    if not (code and 200 <= code < 300):
        error_msg = f"Failed to get backup list - HTTP {code}"
        notify("Backup List Failed", error_msg)
        print(f"❌ {error_msg}")
        return

    # Extract backups from response
    backups = []
    if isinstance(data, dict):
        backups = data.get("results", []) or data.get("backups", []) or data.get("data", [])
    elif isinstance(data, list):
        backups = data

    if not backups:
        notify("No Backups", "No backups found for this install")
        print("❌ No backups found for this install")
        return

    # Find the most recent backup (assuming they're sorted by date or have a created_at field)
    latest_backup = None
    if isinstance(backups[0], dict):
        # Try to sort by created_at, updated_at, or just take the first one
        try:
            latest_backup = max(backups, key=lambda b: b.get("created_at", b.get("updated_at", "")))
        except:
            latest_backup = backups[0]

    if not latest_backup:
        notify("No Backup Found", "Could not determine latest backup")
        print("❌ Could not determine latest backup")
        return

    backup_id = latest_backup.get("id") or latest_backup.get("backup_id") or latest_backup.get("uuid")
    if not backup_id:
        notify("Invalid Backup", "Latest backup has no ID")
        print("❌ Latest backup has no ID")
        return

    # Cache this backup ID
    cache = load_cache()
    if "backup_ids" not in cache:
        cache["backup_ids"] = {}
    cache["backup_ids"][iid] = str(backup_id)
    save_cache(cache)

    # Get status of the latest backup
    status_code, status_data = get_backup_status(iid, backup_id, account)

    if status_code and 200 <= status_code < 300:
        status_info = f"Latest backup status (ID: {backup_id[:8]}...)"
        if isinstance(status_data, dict) and "status" in status_data:
            status_info += f" - Status: {status_data['status']}"
        notify("Latest Backup Status", status_info)
        print(f"📋 {status_info}")
        print(json.dumps(status_data, indent=2))
    else:
        error_msg = f"Failed to get latest backup status - HTTP {status_code}"
        notify("Backup Status Failed", error_msg)
        print(f"❌ {error_msg}")
        print(json.dumps(status_data, indent=2))

def run_install_details(iid: str):
    code, data = get_install_by_id(iid)
    print(json.dumps(data, indent=2))

def run_domains_list(iid: str):
    code, data = list_domains(iid)
    print(json.dumps(data, indent=2))









# -----------------------------------
# Entry
# -----------------------------------
if __name__ == "__main__":
    # action mode
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) > 2 else ""

        if cmd == "refresh":
            do_refresh_installs()

        elif cmd == "clear_cache":
            cache = {"installs": [], "fetched_at": 0, "backup_ids": {}, "accounts_used": []}
            save_cache(cache)
            print("Cache cleared successfully!")
            do_refresh_installs()



        elif cmd == "ssh_term" and arg:
            do_open_terminal(arg, app="Terminal")
        elif cmd == "ssh_iterm" and arg:
            do_open_terminal(arg, app="iTerm2")

        # API actions
        elif cmd == "purge_cache" and arg:
            run_purge_cache(arg)
        elif cmd == "backup_request" and arg:
            run_backup_request(arg)
        elif cmd == "backup_status_prompt" and arg:
            run_backup_status_prompt(arg)

        elif cmd == "latest_backup_status" and arg:
            run_latest_backup_status(arg)
        elif cmd == "install_details" and arg:
            run_install_details(arg)
        elif cmd == "domains_list" and arg:
            run_domains_list(arg)

        sys.exit(0)

    # normal render
    cache = load_cache()
    elapsed_time = int(time.time()) - cache.get("fetched_at", 0)
    print(f"DEBUG REFRESH: Elapsed time: {elapsed_time}s, refresh threshold: {REFRESH_SECS}s", file=sys.stderr)
    if elapsed_time > REFRESH_SECS:
        print(f"DEBUG REFRESH: Auto-refreshing installs", file=sys.stderr)
        do_refresh_installs()
        cache = load_cache()
    else:
        print(f"DEBUG REFRESH: Using cached data", file=sys.stderr)
    # top level menu
    print(f"WPE {len(cache.get('installs', []))}")
    print("---")

    # Add MainWP link if configured
    if MAINWP_LABEL and MAINWP_URL:
        print(f"{MAINWP_LABEL} | href={MAINWP_URL}")
        print("---")


    print(f"Refresh installs now | bash={plugin_path()} param1=refresh terminal=false refresh=true")
    print(f"Clear cache & refresh | bash={plugin_path()} param1=clear_cache terminal=false refresh=true")
    print(f"Cache file: {CACHE_FILE}")
    print("---")
    if cache.get("installs"):
        render_installs_grouped_by_site(cache["installs"])
    else:
        print("[No installs yet]")
        print(f"--Run refresh | bash={plugin_path()} param1=refresh terminal=false refresh=true")
    print("---")
    print(f"Auto refresh every {REFRESH_SECS}s. Change with REFRESH_SECS env.")
