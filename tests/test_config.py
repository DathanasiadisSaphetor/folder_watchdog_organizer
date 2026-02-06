"""Unit tests for the Config class."""

import unittest
import tempfile
import shutil
import yaml
from pathlib import Path

from folder_watchdog_organizer.config import Config


class TestConfig(unittest.TestCase):
    """Test cases for Config."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)

    def test_default_config(self):
        """Test default configuration."""
        config = Config()
        
        self.assertEqual(config.get('watch_directories'), [])
        self.assertEqual(config.get('destination_directory'), './organized')
        self.assertIsNotNone(config.get('organization_rules'))
        self.assertIsNotNone(config.get('logging'))

    def test_load_from_file(self):
        """Test loading configuration from file."""
        # Create test config file
        config_path = Path(self.test_dir) / "test_config.yaml"
        test_config = {
            'watch_directories': ['/test/dir1', '/test/dir2'],
            'destination_directory': '/test/dest',
            'logging': {
                'level': 'DEBUG'
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        # Load config
        config = Config(str(config_path))
        
        # Verify
        self.assertEqual(config.get_watch_directories(), ['/test/dir1', '/test/dir2'])
        self.assertEqual(config.get_destination_directory(), '/test/dest')
        self.assertEqual(config.get_logging_config()['level'], 'DEBUG')

    def test_save_to_file(self):
        """Test saving configuration to file."""
        config = Config()
        config.config['watch_directories'] = ['/save/test']
        
        # Save config
        config_path = Path(self.test_dir) / "saved_config.yaml"
        config.save_to_file(str(config_path))
        
        # Verify file exists
        self.assertTrue(config_path.exists())
        
        # Load and verify content
        with open(config_path, 'r') as f:
            saved_data = yaml.safe_load(f)
        
        self.assertEqual(saved_data['watch_directories'], ['/save/test'])


if __name__ == '__main__':
    unittest.main()
