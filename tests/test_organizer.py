"""Unit tests for the FileOrganizer class."""

import unittest
import tempfile
import shutil
from pathlib import Path

from folder_watchdog_organizer.organizer import FileOrganizer


class TestFileOrganizer(unittest.TestCase):
    """Test cases for FileOrganizer."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = Path(self.test_dir) / "source"
        self.dest_dir = Path(self.test_dir) / "destination"
        
        self.source_dir.mkdir()
        self.dest_dir.mkdir()
        
        # Create organizer
        self.organizer = FileOrganizer(str(self.dest_dir))

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)

    def test_get_file_category_image(self):
        """Test categorization of image files."""
        self.assertEqual(self.organizer.get_file_category("photo.jpg"), "images")
        self.assertEqual(self.organizer.get_file_category("image.png"), "images")
        self.assertEqual(self.organizer.get_file_category("icon.svg"), "images")

    def test_get_file_category_video(self):
        """Test categorization of video files."""
        self.assertEqual(self.organizer.get_file_category("movie.mp4"), "videos")
        self.assertEqual(self.organizer.get_file_category("clip.avi"), "videos")
        self.assertEqual(self.organizer.get_file_category("video.mkv"), "videos")

    def test_get_file_category_document(self):
        """Test categorization of document files."""
        self.assertEqual(self.organizer.get_file_category("report.pdf"), "documents")
        self.assertEqual(self.organizer.get_file_category("letter.docx"), "documents")
        self.assertEqual(self.organizer.get_file_category("note.txt"), "documents")

    def test_get_file_category_code(self):
        """Test categorization of code files."""
        self.assertEqual(self.organizer.get_file_category("script.py"), "code")
        self.assertEqual(self.organizer.get_file_category("app.js"), "code")
        self.assertEqual(self.organizer.get_file_category("program.java"), "code")

    def test_get_file_category_unknown(self):
        """Test categorization of unknown files."""
        self.assertEqual(self.organizer.get_file_category("unknown.xyz"), "others")

    def test_is_downloading(self):
        """Test download detection."""
        self.assertTrue(self.organizer.is_downloading("file.crdownload"))
        self.assertTrue(self.organizer.is_downloading("file.part"))
        self.assertTrue(self.organizer.is_downloading("file.download"))
        self.assertFalse(self.organizer.is_downloading("file.pdf"))

    def test_organize_file_basic(self):
        """Test basic file organization."""
        # Create a test file
        test_file = self.source_dir / "test.txt"
        test_file.write_text("test content")
        
        # Organize the file
        result = self.organizer.organize_file(str(test_file))
        
        # Verify
        self.assertIsNotNone(result)
        self.assertTrue(Path(result).exists())
        self.assertFalse(test_file.exists())
        self.assertTrue("documents" in result)

    def test_organize_file_downloading(self):
        """Test that downloading files are skipped."""
        # Create a downloading file
        test_file = self.source_dir / "downloading.crdownload"
        test_file.write_text("partial content")
        
        # Try to organize
        result = self.organizer.organize_file(str(test_file))
        
        # Verify it was skipped
        self.assertIsNone(result)
        self.assertTrue(test_file.exists())

    def test_organize_file_duplicate(self):
        """Test duplicate file handling."""
        # Create first file and organize it
        test_file1 = self.source_dir / "test.txt"
        test_file1.write_text("content 1")
        result1 = self.organizer.organize_file(str(test_file1))
        
        # Create duplicate and organize it
        test_file2 = self.source_dir / "test.txt"
        test_file2.write_text("content 2")
        result2 = self.organizer.organize_file(str(test_file2))
        
        # Verify both exist with different names
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        self.assertNotEqual(result1, result2)
        self.assertTrue(Path(result1).exists())
        self.assertTrue(Path(result2).exists())

    def test_organize_directory(self):
        """Test organizing all files in a directory."""
        # Create multiple test files
        (self.source_dir / "image.jpg").write_text("image")
        (self.source_dir / "document.pdf").write_text("document")
        (self.source_dir / "code.py").write_text("code")
        
        # Organize directory
        stats = self.organizer.organize_directory(str(self.source_dir))
        
        # Verify statistics
        self.assertEqual(stats['processed'], 3)
        self.assertEqual(stats['moved'], 3)
        self.assertEqual(stats['skipped'], 0)
        
        # Verify source directory is empty
        self.assertEqual(len(list(self.source_dir.iterdir())), 0)


if __name__ == '__main__':
    unittest.main()
