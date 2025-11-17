"""Configuration manager for the Telegram forwarder bot."""
import json
import os
from typing import Dict, List, Any
import threading


class ConfigManager:
    """Thread-safe configuration manager."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._lock = threading.RLock()  # Use RLock instead of Lock for reentrant locking
        self.load()
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        with self._lock:
            if not os.path.exists(self.config_path):
                self._create_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            return self.config
    
    def save(self) -> None:
        """Save configuration to JSON file."""
        with self._lock:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def _create_default_config(self) -> None:
        """Create default configuration file."""
        default_config = {
            "api_credentials": {
                "api_id": 0,
                "api_hash": "",
                "session_name": "forwarder_session"
            },
            "channel_pairs": [],
            "replacement_rules": [],
            "filters": {
                "enabled": False,
                "mode": "whitelist",
                "keywords": []
            },
            "settings": {
                "retry_attempts": 5,
                "retry_delay": 5,
                "flood_wait_extra_delay": 10,
                "max_message_length": 4096,
                "log_level": "INFO"
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        self.config = default_config
    
    def get_api_credentials(self) -> Dict[str, Any]:
        """Get API credentials."""
        return self.config.get("api_credentials", {})
    
    def get_channel_pairs(self) -> List[Dict[str, Any]]:
        """Get list of enabled channel pairs."""
        pairs = self.config.get("channel_pairs", [])
        return [pair for pair in pairs if pair.get("enabled", True)]
    
    def get_all_channel_pairs(self) -> List[Dict[str, Any]]:
        """Get all channel pairs including disabled ones."""
        return self.config.get("channel_pairs", [])
    
    def add_channel_pair(self, source: int, target: int, backfill_count: int = 10) -> None:
        """Add a new channel pair."""
        with self._lock:
            pair = {
                "source": source,
                "target": target,
                "enabled": True,
                "backfill_count": backfill_count
            }
            self.config.setdefault("channel_pairs", []).append(pair)
            self.save()
    
    def remove_channel_pair(self, index: int) -> None:
        """Remove a channel pair by index."""
        with self._lock:
            pairs = self.config.get("channel_pairs", [])
            if 0 <= index < len(pairs):
                pairs.pop(index)
                self.save()
    
    def update_channel_pair(self, index: int, **kwargs) -> None:
        """Update a channel pair."""
        with self._lock:
            pairs = self.config.get("channel_pairs", [])
            if 0 <= index < len(pairs):
                pairs[index].update(kwargs)
                self.save()
    
    def get_replacement_rules(self) -> List[Dict[str, Any]]:
        """Get text replacement rules."""
        return self.config.get("replacement_rules", [])
    
    def add_replacement_rule(self, find: str, replace: str, case_sensitive: bool = False, is_regex: bool = False) -> None:
        """Add a new replacement rule."""
        with self._lock:
            rule = {
                "find": find,
                "replace": replace,
                "case_sensitive": case_sensitive,
                "is_regex": is_regex
            }
            self.config.setdefault("replacement_rules", []).append(rule)
            self.save()
    
    def remove_replacement_rule(self, index: int) -> None:
        """Remove a replacement rule by index."""
        with self._lock:
            rules = self.config.get("replacement_rules", [])
            if 0 <= index < len(rules):
                rules.pop(index)
                self.save()
    
    def update_replacement_rule(self, index: int, **kwargs) -> None:
        """Update a replacement rule."""
        with self._lock:
            rules = self.config.get("replacement_rules", [])
            if 0 <= index < len(rules):
                rules[index].update(kwargs)
                self.save()
    
    def get_filters(self) -> Dict[str, Any]:
        """Get filter settings."""
        return self.config.get("filters", {})
    
    def update_filters(self, **kwargs) -> None:
        """Update filter settings."""
        with self._lock:
            self.config.setdefault("filters", {}).update(kwargs)
            self.save()
    
    def get_settings(self) -> Dict[str, Any]:
        """Get general settings."""
        return self.config.get("settings", {})
    
    def update_settings(self, **kwargs) -> None:
        """Update general settings."""
        with self._lock:
            self.config.setdefault("settings", {}).update(kwargs)
            self.save()

