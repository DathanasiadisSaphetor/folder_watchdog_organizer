"""Configuration management for the folder watchdog organizer."""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the watchdog organizer."""

    DEFAULT_CONFIG = {
        'watch_directories': [],
        'destination_directory': './organized',
        'organization_rules': {
            'skip_hidden_files': True,
            'skip_system_files': True,
            'handle_duplicates': 'rename',  # 'rename', 'skip', or 'overwrite'
        },
        'file_categories': {},  # Custom categories can be added here
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': None  # Optional log file path
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to configuration YAML file (optional)
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_path:
            self.load_from_file(config_path)

    def load_from_file(self, config_path: str):
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to the YAML configuration file
        """
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return

            with open(path, 'r') as f:
                user_config = yaml.safe_load(f)

            if user_config:
                self._merge_config(user_config)
                logger.info(f"Configuration loaded from: {config_path}")
            else:
                logger.warning(f"Empty config file: {config_path}, using defaults")

        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            logger.info("Using default configuration")

    def _merge_config(self, user_config: Dict[str, Any]):
        """
        Merge user configuration with defaults.

        Args:
            user_config: User-provided configuration dictionary
        """
        for key, value in user_config.items():
            if key in self.config:
                if isinstance(value, dict) and isinstance(self.config[key], dict):
                    self.config[key].update(value)
                else:
                    self.config[key] = value
            else:
                self.config[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self.config.get(key, default)

    def get_watch_directories(self) -> list:
        """Get list of directories to watch."""
        return self.config.get('watch_directories', [])

    def get_destination_directory(self) -> str:
        """Get the destination directory for organized files."""
        return self.config.get('destination_directory', './organized')

    def get_organization_rules(self) -> Dict[str, Any]:
        """Get organization rules."""
        return self.config.get('organization_rules', {})

    def get_file_categories(self) -> Dict[str, list]:
        """Get custom file categories."""
        return self.config.get('file_categories', {})

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.config.get('logging', {})

    def save_to_file(self, config_path: str):
        """
        Save current configuration to a YAML file.

        Args:
            config_path: Path where to save the configuration
        """
        try:
            path = Path(config_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)

            logger.info(f"Configuration saved to: {config_path}")

        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")
