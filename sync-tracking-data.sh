#!/bin/bash

# Sync tracking data from SwiftBar plugins directory to working directory
SWIFTBAR_PLUGINS="/Users/adamchiaravalle/Library/Application Support/SwiftBar/Plugins"
WORKING_DIR="/Users/adamchiaravalle/gits/ac-swiftbar-plugins"

if [ -f "$SWIFTBAR_PLUGINS/tracking_numbers.json" ]; then
    cp "$SWIFTBAR_PLUGINS/tracking_numbers.json" "$WORKING_DIR/tracking_numbers.json"
    echo "✅ Synced tracking data to working directory"
    echo "📦 Current tracking numbers:"
    cat "$WORKING_DIR/tracking_numbers.json" | python3 -m json.tool
else
    echo "❌ No tracking data found in SwiftBar plugins directory"
fi

