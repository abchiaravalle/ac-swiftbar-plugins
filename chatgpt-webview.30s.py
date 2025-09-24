#!/usr/bin/env python3
# <bitbar.title>ChatGPT WebView</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>AC</bitbar.author>
# <bitbar.desc>Open ChatGPT in a SwiftBar WebView popover</bitbar.desc>
# <bitbar.dependencies>python3</bitbar.dependencies>

import os
import sys
from datetime import datetime

def render_menu():
    """Render the SwiftBar menu with ChatGPT webview option"""
    
    # Main menu bar item
    print("🤖 ChatGPT")
    print("---")
    
    # Try different webview syntaxes
    print("Open ChatGPT (WebView) | webview=https://chatgpt.com")
    print("Open ChatGPT (Alt) | webview=\"https://chatgpt.com\"")
    print("Open ChatGPT (Simple) | webview=chatgpt.com")
    
    # Additional options
    print("---")
    print("Open in Browser | href=https://chatgpt.com")
    print("Open in Default Browser | bash=open param1=https://chatgpt.com terminal=false")
    print("---")
    print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    print("---")
    print("Debug Info")
    print("--SwiftBar Version Check | bash=swiftbar --version terminal=true")
    print("--Test Simple WebView | webview=https://example.com")

if __name__ == "__main__":
    render_menu()
