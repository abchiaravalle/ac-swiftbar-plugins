#!/usr/bin/env python3
# <bitbar.title>ChatGPT Local</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>AC</bitbar.author>
# <bitbar.desc>Open ChatGPT with local HTML fallback</bitbar.desc>
# <bitbar.dependencies>python3</bitbar.dependencies>

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

def create_chatgpt_html():
    """Create a local HTML file that embeds ChatGPT"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChatGPT - SwiftBar</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #343541;
            color: #ffffff;
        }
        .header {
            background: #202123;
            padding: 15px;
            text-align: center;
            border-bottom: 1px solid #4d4d4f;
        }
        .header h1 {
            margin: 0;
            font-size: 18px;
            color: #ffffff;
        }
        .iframe-container {
            position: relative;
            width: 100%;
            height: 600px;
            border: none;
        }
        iframe {
            width: 100%;
            height: 100%;
            border: none;
            background: #ffffff;
        }
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #8e8ea0;
            font-size: 14px;
        }
        .error {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #ff6b6b;
            text-align: center;
            padding: 20px;
        }
        .fallback {
            padding: 20px;
            text-align: center;
        }
        .fallback a {
            color: #10a37f;
            text-decoration: none;
            font-weight: 500;
        }
        .fallback a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 ChatGPT - SwiftBar</h1>
    </div>
    
    <div class="iframe-container">
        <div class="loading" id="loading">Loading ChatGPT...</div>
        <iframe 
            id="chatgpt-iframe"
            src="https://chatgpt.com" 
            onload="hideLoading()"
            onerror="showError()"
            style="display: none;">
        </iframe>
        <div class="error" id="error" style="display: none;">
            <h3>Unable to load ChatGPT</h3>
            <p>This might be due to iframe restrictions or network issues.</p>
            <div class="fallback">
                <a href="https://chatgpt.com" target="_blank">Open ChatGPT in Browser</a>
            </div>
        </div>
    </div>

    <script>
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('chatgpt-iframe').style.display = 'block';
        }
        
        function showError() {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('error').style.display = 'block';
        }
        
        // Fallback after 5 seconds if iframe doesn't load
        setTimeout(function() {
            if (document.getElementById('loading').style.display !== 'none') {
                showError();
            }
        }, 5000);
    </script>
</body>
</html>
    """
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False)
    temp_file.write(html_content)
    temp_file.close()
    
    return f"file://{temp_file.name}"

def render_menu():
    """Render the SwiftBar menu with ChatGPT options"""
    
    # Main menu bar item
    print("🤖 ChatGPT")
    print("---")
    
    # Try webview first
    print("Open ChatGPT (WebView) | webview=https://chatgpt.com")
    
    # Create local HTML version
    try:
        local_html = create_chatgpt_html()
        print(f"Open ChatGPT (Local) | webview={local_html}")
    except Exception as e:
        print(f"Local HTML Error: {e}")
    
    # Browser options
    print("---")
    print("Open in Browser | href=https://chatgpt.com")
    print("Open in Default Browser | bash=open param1=https://chatgpt.com terminal=false")
    
    # Debug info
    print("---")
    print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    render_menu()
