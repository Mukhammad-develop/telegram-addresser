"""Configuration manager for the Telegram forwarder bot."""
import json
import os
from typing import Dict, List, Any
import threading


class ConfigManager:
    """Thread-safe configuration manager."""
    
    def __init__(self, config_path_or_dict = "config.json"):
        """
        Initialize ConfigManager.
        
        Args:
            config_path_or_dict: Either a file path (str) or a config dict.
                                 If dict, it's used directly without file I/O.
        """
        self.config_path = None
        self.config: Dict[str, Any] = {}
        self._lock = threading.RLock()  # Use RLock instead of Lock for reentrant locking
        
        # Check if it's a dict or a file path
        if isinstance(config_path_or_dict, dict):
            # Use dict directly, no file I/O
            self.config = config_path_or_dict
        else:
            # It's a file path
            self.config_path = config_path_or_dict
            self.load()
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        with self._lock:
            if self.config_path is None:
                # Using dict mode, no file to load
                return self.config
                
            if not os.path.exists(self.config_path):
                self._create_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            return self.config
    
    def save(self) -> None:
        """Save configuration to JSON file."""
        with self._lock:
            if self.config_path is None:
                # Using dict mode, no file to save
                return
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
        
        if self.config_path:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        self.config = default_config
    
    def is_multi_worker_mode(self) -> bool:
        """Check if config is in multi-worker mode."""
        return "workers" in self.config and isinstance(self.config.get("workers"), list)
    
    def get_api_credentials(self) -> Dict[str, Any]:
        """Get API credentials."""
        return self.config.get("api_credentials", {})
    
    def get_channel_pairs(self) -> List[Dict[str, Any]]:
        """Get list of enabled channel pairs."""
        if self.is_multi_worker_mode():
            # In multi-worker mode, aggregate pairs from all workers
            all_pairs = []
            for worker in self.config.get("workers", []):
                if worker.get("enabled", True):
                    pairs = worker.get("channel_pairs", [])
                    all_pairs.extend([p for p in pairs if p.get("enabled", True)])
            return all_pairs
        else:
            pairs = self.config.get("channel_pairs", [])
            return [pair for pair in pairs if pair.get("enabled", True)]
    
    def get_all_channel_pairs(self) -> List[Dict[str, Any]]:
        """Get all channel pairs including disabled ones."""
        if self.is_multi_worker_mode():
            # In multi-worker mode, aggregate pairs from all workers
            all_pairs = []
            for worker in self.config.get("workers", []):
                all_pairs.extend(worker.get("channel_pairs", []))
            return all_pairs
        else:
            return self.config.get("channel_pairs", [])
    
    def add_channel_pair(self, source: int, target: int, backfill_count: int = 10, worker_id: str = None) -> None:
        """
        Add a new channel pair.
        
        Args:
            source: Source channel ID
            target: Target channel ID
            backfill_count: Number of messages to backfill
            worker_id: For multi-worker mode, add to specific worker. If None, adds to first worker.
        """
        with self._lock:
            pair = {
                "source": source,
                "target": target,
                "enabled": True,
                "backfill_count": backfill_count
            }
            
            if self.is_multi_worker_mode():
                workers = self.config.get("workers", [])
                if workers:
                    # Add to specific worker or first worker
                    target_worker = None
                    if worker_id:
                        for worker in workers:
                            if worker.get("worker_id") == worker_id:
                                target_worker = worker
                                break
                    if not target_worker:
                        target_worker = workers[0]  # Default to first worker
                    
                    target_worker.setdefault("channel_pairs", []).append(pair)
            else:
                self.config.setdefault("channel_pairs", []).append(pair)
            
            self.save()
    
    def remove_channel_pair(self, index: int, worker_id: str = None) -> None:
        """
        Remove a channel pair by index.
        
        Args:
            index: Index of pair to remove (in aggregated list for multi-worker)
            worker_id: For multi-worker mode, remove from specific worker
        """
        with self._lock:
            if self.is_multi_worker_mode():
                current_index = 0
                workers = self.config.get("workers", [])
                for worker in workers:
                    if worker_id and worker.get("worker_id") != worker_id:
                        continue
                    
                    pairs = worker.get("channel_pairs", [])
                    if current_index <= index < current_index + len(pairs):
                        local_index = index - current_index
                        pairs.pop(local_index)
                        self.save()
                        return
                    current_index += len(pairs)
            else:
                pairs = self.config.get("channel_pairs", [])
                if 0 <= index < len(pairs):
                    pairs.pop(index)
                    self.save()
    
    def update_channel_pair(self, index: int, worker_id: str = None, **kwargs) -> None:
        """
        Update a channel pair.
        
        Args:
            index: Index of pair to update (in aggregated list for multi-worker)
            worker_id: For multi-worker mode, update in specific worker
            **kwargs: Fields to update
        """
        with self._lock:
            if self.is_multi_worker_mode():
                current_index = 0
                workers = self.config.get("workers", [])
                for worker in workers:
                    if worker_id and worker.get("worker_id") != worker_id:
                        continue
                    
                    pairs = worker.get("channel_pairs", [])
                    if current_index <= index < current_index + len(pairs):
                        local_index = index - current_index
                        pairs[local_index].update(kwargs)
                        self.save()
                        return
                    current_index += len(pairs)
            else:
                pairs = self.config.get("channel_pairs", [])
                if 0 <= index < len(pairs):
                    pairs[index].update(kwargs)
                    self.save()
    
    def get_replacement_rules(self) -> List[Dict[str, Any]]:
        """Get text replacement rules."""
        if self.is_multi_worker_mode():
            # In multi-worker mode, aggregate rules from all workers
            all_rules = []
            for worker in self.config.get("workers", []):
                if worker.get("enabled", True):
                    rules = worker.get("replacement_rules", [])
                    all_rules.extend(rules)
            return all_rules
        else:
            return self.config.get("replacement_rules", [])
    
    def add_replacement_rule(self, find: str, replace: str, case_sensitive: bool = False, is_regex: bool = False, worker_id: str = None) -> None:
        """
        Add a new replacement rule.
        
        Args:
            find: Text to find
            replace: Text to replace with
            case_sensitive: Whether matching is case-sensitive
            is_regex: Whether find pattern is a regex
            worker_id: For multi-worker mode, add to specific worker. If None, adds to all workers.
        """
        with self._lock:
            rule = {
                "find": find,
                "replace": replace,
                "case_sensitive": case_sensitive,
                "is_regex": is_regex
            }
            
            if self.is_multi_worker_mode():
                # Add to worker(s)
                workers = self.config.get("workers", [])
                for worker in workers:
                    # Add to specific worker or all workers
                    if worker_id is None or worker.get("worker_id") == worker_id:
                        worker.setdefault("replacement_rules", []).append(rule)
            else:
                # Single-worker mode
                self.config.setdefault("replacement_rules", []).append(rule)
            
            self.save()
    
    def remove_replacement_rule(self, index: int, worker_id: str = None) -> None:
        """
        Remove a replacement rule by index.
        
        Args:
            index: Index of rule to remove (in aggregated list for multi-worker)
            worker_id: For multi-worker mode, remove from specific worker. If None, removes from all.
        """
        with self._lock:
            if self.is_multi_worker_mode():
                # For multi-worker, we need to find which worker has this rule
                current_index = 0
                workers = self.config.get("workers", [])
                for worker in workers:
                    if not worker.get("enabled", True) and worker_id is None:
                        continue
                    if worker_id and worker.get("worker_id") != worker_id:
                        continue
                        
                    rules = worker.get("replacement_rules", [])
                    if current_index <= index < current_index + len(rules):
                        # This rule is in this worker
                        local_index = index - current_index
                        rules.pop(local_index)
                        self.save()
                        return
                    current_index += len(rules)
            else:
                rules = self.config.get("replacement_rules", [])
                if 0 <= index < len(rules):
                    rules.pop(index)
                    self.save()
    
    def update_replacement_rule(self, index: int, worker_id: str = None, **kwargs) -> None:
        """
        Update a replacement rule.
        
        Args:
            index: Index of rule to update (in aggregated list for multi-worker)
            worker_id: For multi-worker mode, update in specific worker
            **kwargs: Fields to update
        """
        with self._lock:
            if self.is_multi_worker_mode():
                # For multi-worker, find which worker has this rule
                current_index = 0
                workers = self.config.get("workers", [])
                for worker in workers:
                    if not worker.get("enabled", True) and worker_id is None:
                        continue
                    if worker_id and worker.get("worker_id") != worker_id:
                        continue
                        
                    rules = worker.get("replacement_rules", [])
                    if current_index <= index < current_index + len(rules):
                        local_index = index - current_index
                        rules[local_index].update(kwargs)
                        self.save()
                        return
                    current_index += len(rules)
            else:
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

