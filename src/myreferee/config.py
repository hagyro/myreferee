"""
Configuration management for myreferee.

Loads settings from:
1. User config: ~/.config/myreferee/settings.yaml
2. Bundled defaults: package config/settings.yaml
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def get_xdg_config_home() -> Path:
    """Get XDG config home directory."""
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def get_xdg_data_home() -> Path:
    """Get XDG data home directory."""
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def get_config_dir() -> Path:
    """Get myreferee config directory."""
    return get_xdg_config_home() / "myreferee"


def get_data_dir() -> Path:
    """Get myreferee data directory."""
    return get_xdg_data_home() / "myreferee"


def get_reviews_dir() -> Path:
    """Get directory for storing reviews."""
    reviews_dir = get_data_dir() / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    return reviews_dir


def get_sessions_dir() -> Path:
    """Get directory for storing sessions."""
    sessions_dir = get_data_dir() / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def load_settings(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load settings from config file.

    Priority:
    1. Explicit config_path if provided
    2. User config: ~/.config/myreferee/settings.yaml
    3. Bundled default config

    Args:
        config_path: Optional explicit path to config file

    Returns:
        Dictionary of settings
    """
    # Default settings
    default_settings = {
        "api": {
            "model": "claude-sonnet-4-20250514",
            "scopus": {
                "base_url": "https://api.elsevier.com/content/search/scopus",
                "results_per_journal": 30,
                "years_back": 5,
            },
        },
        "journal_research": {
            "min_articles": 20,
            "max_articles": 40,
            "priority_years": 3,
        },
        "paper_processing": {
            "formats": [".pdf", ".docx", ".doc", ".tex"],
            "max_size_mb": 50,
        },
        "output": {
            "format": "markdown",
            "include": {
                "summary": True,
                "contribution_assessment": True,
                "major_concerns": True,
                "minor_concerns": True,
                "robustness_checklist": True,
                "section_rewrites": True,
                "positioning_analysis": True,
                "editor_note": True,
                "todo_list": True,
            },
        },
        "sessions": {
            "expiry_days": 30,
            "max_sessions": 100,
        },
    }

    # Try to load from explicit path
    if config_path and config_path.exists():
        with open(config_path, "r") as f:
            user_settings = yaml.safe_load(f) or {}
        return _merge_settings(default_settings, user_settings)

    # Try user config directory
    user_config = get_config_dir() / "settings.yaml"
    if user_config.exists():
        with open(user_config, "r") as f:
            user_settings = yaml.safe_load(f) or {}
        return _merge_settings(default_settings, user_settings)

    # Try bundled config (relative to package)
    package_dir = Path(__file__).parent.parent.parent
    bundled_config = package_dir / "config" / "settings.yaml"
    if bundled_config.exists():
        with open(bundled_config, "r") as f:
            bundled_settings = yaml.safe_load(f) or {}
        return _merge_settings(default_settings, bundled_settings)

    return default_settings


def _merge_settings(base: Dict, override: Dict) -> Dict:
    """Deep merge two settings dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_settings(result[key], value)
        else:
            result[key] = value
    return result


def get_elsevier_api_key() -> Optional[str]:
    """Get Elsevier API key from environment."""
    return os.environ.get("ELSEVIER_API_KEY")


class Settings:
    """Configuration singleton for myreferee."""

    _instance: Optional["Settings"] = None
    _settings: Dict[str, Any]

    def __new__(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = load_settings()
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting by dot-notation key (e.g., 'api.model')."""
        keys = key.split(".")
        value = self._settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def reload(self, config_path: Optional[Path] = None) -> None:
        """Reload settings from config file."""
        self._settings = load_settings(config_path)

    @property
    def reviews_dir(self) -> Path:
        """Get reviews directory."""
        return get_reviews_dir()

    @property
    def sessions_dir(self) -> Path:
        """Get sessions directory."""
        return get_sessions_dir()

    @property
    def elsevier_api_key(self) -> Optional[str]:
        """Get Elsevier API key."""
        return get_elsevier_api_key()


# Global settings instance
settings = Settings()
