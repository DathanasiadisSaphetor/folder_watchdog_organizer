# Folder Watchdog Organizer

A Python-based folder watchdog service that monitors specific folders for file changes and automatically organizes them based on file types, content, and download status.

## Features

- **Real-time Monitoring**: Watches specified folders for file changes (creation, modification, movement)
- **Automatic Organization**: Categorizes and moves files to organized destination folders
- **Smart File Detection**: 
  - Detects file types (images, videos, documents, code, etc.)
  - Identifies files currently being downloaded
  - Handles existing files in watch directories
- **Flexible Configuration**: YAML-based configuration for easy customization
- **Duplicate Handling**: Configurable strategies for handling duplicate files
- **Extensive Logging**: Detailed logging for monitoring and debugging
- **CLI Interface**: Easy-to-use command-line interface

## Installation

### From Source

1. Clone the repository:
```bash
git clone https://github.com/DathanasiadisSaphetor/folder_watchdog_organizer.git
cd folder_watchdog_organizer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package:
```bash
pip install -e .
```

## Usage

### Quick Start

Monitor a folder and organize files:

```bash
folder-watchdog -w /path/to/downloads -d /path/to/organized
```

### Using Configuration File

1. Generate a sample configuration:
```bash
folder-watchdog --generate-config config.yaml
```

2. Edit the configuration file to specify your watch directories and preferences.

3. Run with configuration:
```bash
folder-watchdog -c config.yaml
```

### Command-Line Options

```
usage: folder-watchdog [-h] [-c CONFIG] [-w WATCH] [-d DESTINATION]
                       [--no-organize-existing] [--generate-config PATH]

Folder Watchdog Organizer - Monitor and organize files automatically

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to configuration file (YAML)
  -w WATCH, --watch WATCH
                        Directory to watch (can be specified multiple times)
  -d DESTINATION, --destination DESTINATION
                        Destination directory for organized files
  --no-organize-existing
                        Skip organizing existing files
  --generate-config PATH
                        Generate a sample configuration file
```

## Configuration

The service uses a YAML configuration file. See `config.example.yaml` for a complete example.

### Configuration Options

- **watch_directories**: List of directories to monitor
- **destination_directory**: Base directory for organized files
- **organization_rules**: Rules for file organization
  - `skip_hidden_files`: Whether to skip hidden files
  - `skip_system_files`: Whether to skip system files
  - `handle_duplicates`: How to handle duplicates ('rename', 'skip', 'overwrite')
- **file_categories**: Custom file type categories
- **logging**: Logging configuration (level, format, file)

## File Categories

Files are automatically organized into the following categories:

- **images**: .jpg, .jpeg, .png, .gif, .bmp, .svg, .webp, .ico, .tiff
- **videos**: .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm, .m4v
- **audio**: .mp3, .wav, .flac, .aac, .ogg, .wma, .m4a
- **documents**: .pdf, .doc, .docx, .txt, .rtf, .odt, .tex
- **spreadsheets**: .xls, .xlsx, .csv, .ods
- **presentations**: .ppt, .pptx, .odp
- **archives**: .zip, .rar, .7z, .tar, .gz, .bz2, .xz
- **code**: .py, .js, .java, .cpp, .c, .h, .cs, .php, .rb, .go, .rs
- **executables**: .exe, .msi, .app, .deb, .rpm
- **others**: Any file that doesn't match the above categories

You can add custom categories in the configuration file.

## How It Works

1. **Initial Scan**: When started, the service scans watch directories and organizes existing files (unless `--no-organize-existing` is used)
2. **Real-time Monitoring**: Watches for file system events (create, modify, move)
3. **Download Detection**: Identifies files being downloaded (e.g., .crdownload, .part files) and waits for completion
4. **Categorization**: Determines file category based on extension
5. **Organization**: Moves files to appropriate subdirectories in the destination folder
6. **Duplicate Handling**: Renames files if duplicates exist (configurable)

## Examples

### Example 1: Monitor Downloads Folder

```bash
folder-watchdog -w ~/Downloads -d ~/Organized
```

### Example 2: Monitor Multiple Folders

```bash
folder-watchdog -w ~/Downloads -w ~/Desktop -d ~/Organized
```

### Example 3: Using Configuration File

Create `config.yaml`:
```yaml
watch_directories:
  - /home/user/Downloads
  - /home/user/Desktop

destination_directory: /home/user/Organized

organization_rules:
  skip_hidden_files: true
  handle_duplicates: rename

logging:
  level: INFO
  file: /var/log/watchdog.log
```

Run:
```bash
folder-watchdog -c config.yaml
```

## Requirements

- Python 3.7+
- watchdog >= 3.0.0
- pyyaml >= 6.0
- python-magic >= 0.4.27

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.