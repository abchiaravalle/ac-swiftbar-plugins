# Package Tracker SwiftBar Plugin

A SwiftBar plugin that tracks packages from UPS, USPS, FedEx, and DHL, displaying current status, location, and expected delivery date directly in your macOS menu bar.

## Features

- **Multi-Carrier Support**: Track packages from UPS, USPS, FedEx, and DHL
- **Automatic Carrier Detection**: Automatically detects the carrier based on tracking number format
- **Real-Time Status**: Shows current status with color-coded indicators
- **Location Tracking**: Displays current package location
- **Delivery Date**: Shows expected or actual delivery date
- **Easy Management**: Add/remove tracking numbers through the menu
- **Caching**: Intelligent caching to avoid excessive API calls
- **Auto-Refresh**: Updates every 5 minutes automatically

## Installation

1. **Install Dependencies**:
   ```bash
   pip3 install requests beautifulsoup4
   ```

2. **Make the script executable**:
   ```bash
   chmod +x package-tracker.5m.py
   ```

3. **Add to SwiftBar**:
   - Copy `package-tracker.5m.py` to your SwiftBar plugins folder
   - SwiftBar will automatically detect and run the plugin

## Usage

### Adding Tracking Numbers

1. Click on the 📦 icon in your menu bar
2. Select "Add tracking number"
3. Enter your tracking number in the dialog
4. The plugin will automatically detect the carrier and start tracking

### Supported Tracking Number Formats

**UPS**:
- `1Z` followed by 16-18 alphanumeric characters
- `T` followed by 10 digits

**USPS**:
- 20-22 digit numbers
- `XX` + 9 digits + `US` format
- 13-15 digit numbers

**FedEx**:
- 12, 14, 15, 20, or 22 digit numbers

**DHL**:
- 9-12 digit numbers
- `JD` + 18 digits format

### Menu Features

- **Status Icons**: 
  - ✅ Delivered
  - 🚚 In Transit
  - 🚛 Out for Delivery
  - ⚠️ Exception
  - ⏳ Pending
  - ❓ Unknown

- **Color Coding**:
  - Green: Delivered
  - Blue: In Transit
  - Orange: Out for Delivery
  - Red: Exception
  - Yellow: Pending
  - Gray: Unknown

### Management Options

- **Refresh all packages**: Manually refresh tracking data for all packages
- **Add tracking number**: Add new packages to track (automatically fetches initial status)
- **Remove**: Remove individual tracking numbers
- **Clear all packages**: Remove all tracking numbers
- **Auto-refresh**: Updates every 5 minutes

## Configuration

### Cache Settings

The plugin caches tracking data for 5 minutes to avoid excessive API calls. Cache files are stored in:
- `~/.cache/swiftbar_package_tracker_cache.json`

### Tracking Numbers Storage

Tracking numbers are stored in:
- `tracking_numbers.json` (in the same directory as the plugin)

## Technical Details

### How It Works

1. **Carrier Detection**: Uses regex patterns to identify carriers based on tracking number format
2. **Web Scraping**: Fetches tracking information by scraping carrier websites with multiple URL fallbacks
3. **Data Parsing**: Extracts status, location, and delivery date from HTML responses
4. **Caching**: Stores results to minimize API calls and improve performance
5. **Menu Rendering**: Formats data for SwiftBar display with icons and colors
6. **Auto-Refresh**: Automatically fetches initial status when adding new packages

### Error Handling

- Network timeouts are handled gracefully
- Invalid tracking numbers are detected and reported
- API failures fall back to cached data when available
- Debug information is logged to stderr

### Performance

- 5-minute cache duration reduces API calls
- Parallel processing for multiple tracking numbers
- Efficient regex matching for carrier detection
- Minimal memory footprint

## Troubleshooting

### Common Issues

1. **"Could not detect carrier"**:
   - Check that your tracking number matches the supported formats
   - Ensure the tracking number is entered correctly

2. **"Unknown status"**:
   - The carrier website may have changed its format
   - Network connectivity issues
   - Tracking number may be too new or invalid

3. **Plugin not appearing**:
   - Ensure the script is executable (`chmod +x`)
   - Check that SwiftBar is running
   - Verify the script is in the correct plugins folder

### Debug Mode

To see debug information, run the plugin from terminal:
```bash
python3 package-tracker.5m.py
```

Debug output will show:
- Cache operations
- API requests
- Error messages
- Processing steps

## Limitations

- **Web Scraping**: Relies on carrier websites, which may change
- **Rate Limiting**: Some carriers may block frequent requests
- **Accuracy**: Parsing may not be 100% accurate due to website changes
- **Authentication**: No official API access (uses public tracking pages)

## Future Enhancements

- Official API integration when available
- More detailed location information
- Delivery notifications
- Package history tracking
- Multiple user support
- Export/import tracking lists

## Contributing

Feel free to submit issues and enhancement requests. The plugin is designed to be easily extensible for additional carriers or features.

## License

This plugin is provided as-is for personal use. Please respect carrier websites' terms of service when using web scraping functionality.
