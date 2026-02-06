"""Main entry point for the folder watchdog organizer."""

import sys
import time
import logging
import argparse
from pathlib import Path
from typing import List

from .config import Config
from .organizer import FileOrganizer
from .watchdog import FileWatchdog

logger = logging.getLogger(__name__)


class FolderWatchdogOrganizer:
    """Main orchestrator for the folder watchdog organizer service."""

    def __init__(self, config: Config):
        """
        Initialize the organizer service.

        Args:
            config: Configuration object
        """
        self.config = config
        self.organizer = FileOrganizer(
            destination_base=config.get_destination_directory(),
            rules=config.get_organization_rules()
        )
        self.watchdogs: List[FileWatchdog] = []
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging based on configuration."""
        log_config = self.config.get_logging_config()
        level = getattr(logging, log_config.get('level', 'INFO').upper())
        log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = log_config.get('file')

        # Configure root logger
        logging.basicConfig(
            level=level,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
            ] + ([logging.FileHandler(log_file)] if log_file else [])
        )

    def _handle_file_event(self, file_path: str, event_type: str):
        """
        Handle file system events.

        Args:
            file_path: Path to the file
            event_type: Type of event (created, modified, moved)
        """
        logger.info(f"File event detected: {event_type} - {file_path}")

        # Wait a bit to ensure file is completely written
        time.sleep(0.5)

        # Organize the file
        result = self.organizer.organize_file(file_path)
        
        if result:
            logger.info(f"File organized successfully: {file_path} -> {result}")
        else:
            logger.debug(f"File not organized: {file_path}")

    def organize_existing_files(self, directories: List[str]):
        """
        Organize existing files in the watch directories.

        Args:
            directories: List of directories to organize
        """
        logger.info("Organizing existing files...")
        
        for directory in directories:
            logger.info(f"Processing directory: {directory}")
            stats = self.organizer.organize_directory(directory)
            logger.info(f"Statistics: {stats}")

    def start_watching(self, directories: List[str]):
        """
        Start watching directories for changes.

        Args:
            directories: List of directories to watch
        """
        logger.info("Starting watchdog service...")

        # Create watchdogs for each directory
        for directory in directories:
            try:
                watchdog = FileWatchdog(directory, self._handle_file_event)
                watchdog.start()
                self.watchdogs.append(watchdog)
                logger.info(f"Watching: {directory}")
            except Exception as e:
                logger.error(f"Failed to watch {directory}: {e}")

        if not self.watchdogs:
            logger.error("No directories are being watched. Exiting.")
            return

        # Keep running until interrupted
        try:
            logger.info("Service is running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        finally:
            self.stop()

    def stop(self):
        """Stop all watchdogs."""
        logger.info("Stopping watchdog service...")
        
        for watchdog in self.watchdogs:
            watchdog.stop()
        
        self.watchdogs.clear()
        logger.info("Service stopped")

    def run(self, organize_existing: bool = True):
        """
        Run the complete service.

        Args:
            organize_existing: Whether to organize existing files first
        """
        directories = self.config.get_watch_directories()

        if not directories:
            logger.error("No watch directories configured. Exiting.")
            return

        # Validate directories
        valid_directories = []
        for directory in directories:
            path = Path(directory)
            if path.exists() and path.is_dir():
                valid_directories.append(directory)
            else:
                logger.warning(f"Invalid directory, skipping: {directory}")

        if not valid_directories:
            logger.error("No valid watch directories found. Exiting.")
            return

        # Organize existing files if requested
        if organize_existing:
            self.organize_existing_files(valid_directories)

        # Start watching for new files
        self.start_watching(valid_directories)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Folder Watchdog Organizer - Monitor and organize files automatically'
    )
    parser.add_argument(
        '-c', '--config',
        help='Path to configuration file (YAML)',
        default=None
    )
    parser.add_argument(
        '-w', '--watch',
        help='Directory to watch (can be specified multiple times)',
        action='append',
        default=None
    )
    parser.add_argument(
        '-d', '--destination',
        help='Destination directory for organized files',
        default=None
    )
    parser.add_argument(
        '--no-organize-existing',
        help='Skip organizing existing files',
        action='store_true'
    )
    parser.add_argument(
        '--generate-config',
        help='Generate a sample configuration file',
        metavar='PATH'
    )

    args = parser.parse_args()

    # Generate config if requested
    if args.generate_config:
        config = Config()
        config.save_to_file(args.generate_config)
        print(f"Sample configuration generated at: {args.generate_config}")
        return

    # Load configuration
    config = Config(args.config)

    # Override with command line arguments
    if args.watch:
        config.config['watch_directories'] = args.watch
    if args.destination:
        config.config['destination_directory'] = args.destination

    # Create and run the service
    try:
        service = FolderWatchdogOrganizer(config)
        service.run(organize_existing=not args.no_organize_existing)
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
