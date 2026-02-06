# Quick Start Guide

Get started with Folder Watchdog Organizer in 5 minutes!

## Installation

```bash
# Clone the repository
git clone https://github.com/DathanasiadisSaphetor/folder_watchdog_organizer.git
cd folder_watchdog_organizer

# Install the package
pip install -e .
```

## Quick Test

```bash
# Create test directories
mkdir ~/test_watch ~/test_organized

# Create some test files
cd ~/test_watch
touch photo.jpg document.pdf movie.mp4 code.py

# Run the organizer
folder-watchdog -w ~/test_watch -d ~/test_organized

# Check the results
ls ~/test_organized/*/
```

You should see your files organized into categories!

## Next Steps

1. **Customize for your needs:**
   ```bash
   folder-watchdog --generate-config my-config.yaml
   # Edit my-config.yaml to add your folders
   ```

2. **Run with your configuration:**
   ```bash
   folder-watchdog -c my-config.yaml
   ```

3. **Set up as a service** (see USAGE_EXAMPLES.md)

## Key Features

- ✅ **Real-time monitoring** - Automatically organizes new files
- ✅ **Smart categorization** - 10+ file type categories
- ✅ **Download detection** - Waits for downloads to complete
- ✅ **Duplicate handling** - Automatic renaming of duplicates
- ✅ **Customizable** - Add your own categories via config

## Need Help?

- See [README.md](README.md) for full documentation
- See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) for detailed examples
- Check the example config: [config.example.yaml](config.example.yaml)

## Common Commands

```bash
# Monitor a single folder
folder-watchdog -w ~/Downloads -d ~/Organized

# Monitor multiple folders
folder-watchdog -w ~/Downloads -w ~/Desktop -d ~/Organized

# Skip organizing existing files
folder-watchdog -w ~/Downloads -d ~/Organized --no-organize-existing

# Use a config file
folder-watchdog -c my-config.yaml

# Get help
folder-watchdog --help
```

Happy organizing! 🎉
