"""File watchdog module for monitoring folder changes."""

import time
import logging
from pathlib import Path
from typing import Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, FileMovedEvent

logger = logging.getLogger(__name__)


class FileWatchdogHandler(FileSystemEventHandler):
    """Handler for file system events."""

    def __init__(self, callback: Callable[[str, str], None]):
        """
        Initialize the handler.

        Args:
            callback: Function to call when a file event occurs.
                     Takes (file_path, event_type) as arguments.
        """
        super().__init__()
        self.callback = callback

    def on_created(self, event: FileSystemEvent):
        """Called when a file or directory is created."""
        if not event.is_directory:
            logger.debug(f"File created: {event.src_path}")
            self.callback(event.src_path, 'created')

    def on_modified(self, event: FileSystemEvent):
        """Called when a file or directory is modified."""
        if not event.is_directory:
            logger.debug(f"File modified: {event.src_path}")
            self.callback(event.src_path, 'modified')

    def on_moved(self, event: FileSystemEvent):
        """Called when a file or directory is moved."""
        if not event.is_directory:
            # For move events, use dest_path from FileMovedEvent
            if isinstance(event, FileMovedEvent):
                logger.debug(f"File moved: {event.src_path} -> {event.dest_path}")
                self.callback(event.dest_path, 'moved')
            else:
                logger.debug(f"File moved: {event.src_path}")
                self.callback(event.src_path, 'moved')


class FileWatchdog:
    """Watches a folder for file changes and triggers organization."""

    def __init__(self, watch_path: str, organizer_callback: Callable[[str, str], None]):
        """
        Initialize the FileWatchdog.

        Args:
            watch_path: Path to the folder to watch
            organizer_callback: Callback function for file events
        """
        self.watch_path = Path(watch_path)
        self.organizer_callback = organizer_callback
        self.observer = None
        self.is_running = False

        # Validate watch path
        if not self.watch_path.exists():
            raise ValueError(f"Watch path does not exist: {watch_path}")
        if not self.watch_path.is_dir():
            raise ValueError(f"Watch path is not a directory: {watch_path}")

    def start(self):
        """Start watching the folder."""
        if self.is_running:
            logger.warning("Watchdog is already running")
            return

        logger.info(f"Starting watchdog for: {self.watch_path}")
        
        # Create event handler
        event_handler = FileWatchdogHandler(self.organizer_callback)
        
        # Create and start observer
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_path), recursive=False)
        self.observer.start()
        self.is_running = True
        
        logger.info("Watchdog started successfully")

    def stop(self):
        """Stop watching the folder."""
        if not self.is_running:
            logger.warning("Watchdog is not running")
            return

        logger.info("Stopping watchdog...")
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        
        self.is_running = False
        logger.info("Watchdog stopped")

    def run(self):
        """Run the watchdog indefinitely (blocks until interrupted)."""
        try:
            self.start()
            logger.info("Press Ctrl+C to stop...")
            
            # Keep the main thread alive
            while self.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()
