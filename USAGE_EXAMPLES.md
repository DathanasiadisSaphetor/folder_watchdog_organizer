# Usage Examples for Folder Watchdog Organizer

This document provides practical examples of how to use the Folder Watchdog Organizer service.

## Example 1: Basic Usage - Monitor Downloads Folder

Monitor your Downloads folder and organize files into an "Organized" directory:

```bash
folder-watchdog -w ~/Downloads -d ~/Organized
```

This will:
1. Scan all existing files in ~/Downloads and organize them
2. Start monitoring ~/Downloads for new files
3. Automatically move and categorize new files as they appear

## Example 2: Monitor Multiple Folders

Monitor both Downloads and Desktop folders:

```bash
folder-watchdog -w ~/Downloads -w ~/Desktop -d ~/Organized
```

## Example 3: Skip Organizing Existing Files

If you only want to monitor for new files without organizing existing ones:

```bash
folder-watchdog -w ~/Downloads -d ~/Organized --no-organize-existing
```

## Example 4: Using Configuration File

Create a configuration file `my_config.yaml`:

```yaml
watch_directories:
  - /home/user/Downloads
  - /home/user/Desktop
  - /home/user/Documents/ToOrganize

destination_directory: /home/user/Organized

organization_rules:
  skip_hidden_files: true
  handle_duplicates: rename

file_categories:
  data:
    - .json
    - .xml
    - .yaml
    - .csv
  design:
    - .psd
    - .ai
    - .sketch

logging:
  level: INFO
  file: /var/log/folder_watchdog.log
```

Run with the configuration:

```bash
folder-watchdog -c my_config.yaml
```

## Example 5: Generate Sample Configuration

Generate a sample configuration file to customize:

```bash
folder-watchdog --generate-config config.yaml
```

Then edit the file and run:

```bash
folder-watchdog -c config.yaml
```

## File Organization Structure

After running the service, your destination folder will have this structure:

```
Organized/
├── images/          # .jpg, .png, .gif, etc.
├── videos/          # .mp4, .avi, .mkv, etc.
├── audio/           # .mp3, .wav, .flac, etc.
├── documents/       # .pdf, .doc, .txt, etc.
├── spreadsheets/    # .xls, .xlsx, .csv, etc.
├── presentations/   # .ppt, .pptx, etc.
├── archives/        # .zip, .rar, .7z, etc.
├── code/            # .py, .js, .java, etc.
├── executables/     # .exe, .msi, etc.
└── others/          # Everything else
```

## Example 6: Custom Categories

Add custom file categories in your config file:

```yaml
file_categories:
  ebooks:
    - .epub
    - .mobi
    - .azw
  3d_models:
    - .obj
    - .fbx
    - .blend
    - .stl
```

## Download Detection

The service automatically detects files being downloaded and skips them:

- Files with `.crdownload` extension (Chrome)
- Files with `.part` extension (Firefox)
- Files with `.download` extension
- Files with `.tmp` extension

Once the download completes and the file extension changes, the service will organize it.

## Logging Levels

Adjust logging verbosity in your config:

```yaml
logging:
  level: DEBUG  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

- **DEBUG**: Detailed information for debugging
- **INFO**: General information about operations (recommended)
- **WARNING**: Warning messages
- **ERROR**: Error messages only
- **CRITICAL**: Critical errors only

## Duplicate Handling

Configure how duplicates are handled:

```yaml
organization_rules:
  handle_duplicates: rename  # Options: rename, skip, overwrite
```

- **rename**: Add a number suffix (file_1.txt, file_2.txt)
- **skip**: Don't move the duplicate file
- **overwrite**: Replace the existing file

## Running as a System Service

To run the watchdog as a background service on Linux, create a systemd service file:

```ini
[Unit]
Description=Folder Watchdog Organizer
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username
ExecStart=/usr/local/bin/folder-watchdog -c /home/your-username/watchdog-config.yaml
Restart=always

[Install]
WantedBy=multi-user.target
```

Save as `/etc/systemd/system/folder-watchdog.service`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable folder-watchdog
sudo systemctl start folder-watchdog
```

## Troubleshooting

### Service won't start
- Check that watch directories exist
- Verify you have read/write permissions
- Check the log file for errors

### Files not being organized
- Ensure files are not being downloaded (check extension)
- Check file permissions
- Verify the destination directory is writable

### Too many log messages
- Reduce logging level to WARNING or ERROR
- Disable debug logging in the config
