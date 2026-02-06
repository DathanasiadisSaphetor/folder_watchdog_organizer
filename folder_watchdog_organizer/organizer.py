"""File organizer module for categorizing and moving files."""

import os
import shutil
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FileOrganizer:
    """Organizes files based on type, content, and other criteria."""

    # Default file type categories
    FILE_CATEGORIES = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff'],
        'videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
        'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.tex'],
        'spreadsheets': ['.xls', '.xlsx', '.csv', '.ods'],
        'presentations': ['.ppt', '.pptx', '.odp'],
        'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
        'code': ['.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs'],
        'executables': ['.exe', '.msi', '.app', '.deb', '.rpm'],
        'others': []  # Catch-all category
    }

    # Extensions that indicate a file is being downloaded
    DOWNLOAD_EXTENSIONS = ['.crdownload', '.part', '.download', '.tmp']

    def __init__(self, destination_base: str, rules: Optional[Dict] = None):
        """
        Initialize the FileOrganizer.

        Args:
            destination_base: Base directory where files will be organized
            rules: Custom organization rules (optional)
        """
        self.destination_base = Path(destination_base)
        self.destination_base.mkdir(parents=True, exist_ok=True)
        self.rules = rules or {}
        self._setup_categories()

    def _setup_categories(self):
        """Create category directories if they don't exist."""
        for category in self.FILE_CATEGORIES.keys():
            category_path = self.destination_base / category
            category_path.mkdir(exist_ok=True)

    def get_file_category(self, file_path: str) -> str:
        """
        Determine the category of a file based on its extension.

        Args:
            file_path: Path to the file

        Returns:
            Category name as string
        """
        ext = Path(file_path).suffix.lower()

        for category, extensions in self.FILE_CATEGORIES.items():
            if ext in extensions:
                return category

        return 'others'

    def is_downloading(self, file_path: str) -> bool:
        """
        Check if a file is currently being downloaded.

        Args:
            file_path: Path to the file

        Returns:
            True if file appears to be downloading, False otherwise
        """
        ext = Path(file_path).suffix.lower()
        return ext in self.DOWNLOAD_EXTENSIONS

    def get_destination_path(self, file_path: str, category: str) -> Path:
        """
        Get the destination path for a file.

        Args:
            file_path: Source file path
            category: File category

        Returns:
            Destination Path object
        """
        file_name = Path(file_path).name
        dest_path = self.destination_base / category / file_name

        # Handle name conflicts
        counter = 1
        original_dest = dest_path
        while dest_path.exists():
            stem = original_dest.stem
            suffix = original_dest.suffix
            dest_path = original_dest.parent / f"{stem}_{counter}{suffix}"
            counter += 1

        return dest_path

    def organize_file(self, file_path: str) -> Optional[str]:
        """
        Organize a single file by moving it to the appropriate category folder.

        Args:
            file_path: Path to the file to organize

        Returns:
            Destination path if successful, None otherwise
        """
        try:
            source = Path(file_path)

            # Skip if file doesn't exist
            if not source.exists() or not source.is_file():
                logger.warning(f"File does not exist or is not a file: {file_path}")
                return None

            # Skip if file is being downloaded
            if self.is_downloading(file_path):
                logger.info(f"Skipping file being downloaded: {file_path}")
                return None

            # Determine category
            category = self.get_file_category(file_path)
            logger.info(f"File '{source.name}' categorized as: {category}")

            # Get destination path
            dest_path = self.get_destination_path(file_path, category)

            # Move the file
            shutil.move(str(source), str(dest_path))
            logger.info(f"Moved '{source.name}' to '{dest_path}'")

            return str(dest_path)

        except Exception as e:
            logger.error(f"Error organizing file {file_path}: {e}")
            return None

    def organize_directory(self, source_dir: str) -> Dict[str, int]:
        """
        Organize all files in a directory.

        Args:
            source_dir: Directory to organize

        Returns:
            Dictionary with statistics (files processed, moved, skipped)
        """
        stats = {'processed': 0, 'moved': 0, 'skipped': 0, 'errors': 0}
        source_path = Path(source_dir)

        if not source_path.exists() or not source_path.is_dir():
            logger.error(f"Source directory does not exist: {source_dir}")
            return stats

        for file_path in source_path.iterdir():
            if file_path.is_file():
                stats['processed'] += 1
                result = self.organize_file(str(file_path))
                
                if result:
                    stats['moved'] += 1
                elif self.is_downloading(str(file_path)):
                    stats['skipped'] += 1
                else:
                    stats['errors'] += 1

        return stats
