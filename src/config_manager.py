"""Configuration manager for the Telegram forwarder bot."""
import json
import os
import sqlite3
import threading
from typing import Dict, List, Any, Optional, Tuple


DEFAULT_FILTERS = {
    "enabled": False,
    "mode": "whitelist",
    "keywords": []
}

DEFAULT_SETTINGS = {
    "retry_attempts": 5,
    "retry_delay": 5,
    "flood_wait_extra_delay": 10,
    "max_message_length": 4096,
    "log_level": "INFO",
    "add_source_link": False,
    "source_link_text": "\n\n🔗 Source: {link}"
}

DEFAULT_API_CREDENTIALS = {
    "api_id": 0,
    "api_hash": "",
    "session_name": "forwarder_session"
}

DEFAULT_WORKER_ID = "default"


class ConfigManager:
    """Thread-safe configuration manager backed by SQLite."""

    def __init__(self, config_path_or_dict="config.json", db_path: Optional[str] = None):
        """
        Initialize ConfigManager.

        Args:
            config_path_or_dict: Either a file path (str) or a config dict.
                                 If dict, it's used directly without file I/O.
            db_path: Optional SQLite DB path (defaults to config.db next to config.json).
        """
        self.config_path = None
        self.db_path = None
        self.config: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._dict_mode = False
        self._config_mode = "single"

        if isinstance(config_path_or_dict, dict):
            self._dict_mode = True
            self.config = config_path_or_dict
        else:
            self.config_path = config_path_or_dict
            if db_path is None:
                base_dir = os.path.dirname(self.config_path) or "."
                self.db_path = os.path.join(base_dir, "config.db")
            else:
                self.db_path = db_path
            self.load()

    def load(self) -> Dict[str, Any]:
        """Load configuration from SQLite and admin JSON."""
        with self._lock:
            if self._dict_mode:
                return self.config

            admin_config, full_config = self._load_json_config()
            self._init_db()

            if self._should_migrate(full_config):
                self.config = full_config
                self.save()
                admin_config, _ = self._load_json_config()

            self.config = self._build_config_from_db(admin_config)
            return self.config

    def save(self) -> None:
        """Save configuration to SQLite and admin JSON."""
        with self._lock:
            if self._dict_mode:
                return
            admin_config = {
                "admin_bot_token": self.config.get("admin_bot_token", ""),
                "admin_user_ids": self.config.get("admin_user_ids", [])
            }
            self._save_admin_config(admin_config)
            self._write_db_from_config(self.config)

    def _load_json_config(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Load admin config from JSON; return (admin_config, full_config)."""
        if not self.config_path:
            admin_config = {"admin_bot_token": "", "admin_user_ids": []}
            return admin_config, dict(admin_config)

        if not os.path.exists(self.config_path):
            admin_config = {"admin_bot_token": "", "admin_user_ids": []}
            self._save_admin_config(admin_config)
            return admin_config, dict(admin_config)

        with open(self.config_path, "r", encoding="utf-8") as f:
            full_config = json.load(f)

        admin_config = {
            "admin_bot_token": full_config.get("admin_bot_token", ""),
            "admin_user_ids": full_config.get("admin_user_ids", [])
        }
        return admin_config, full_config

    def _save_admin_config(self, admin_config: Dict[str, Any]) -> None:
        """Save only admin config fields to JSON."""
        if not self.config_path:
            return
        safe_admin = {
            "admin_bot_token": admin_config.get("admin_bot_token", ""),
            "admin_user_ids": admin_config.get("admin_user_ids", [])
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(safe_admin, f, indent=2, ensure_ascii=False)

    def _should_migrate(self, full_config: Dict[str, Any]) -> bool:
        """Detect legacy JSON config that needs migration."""
        legacy_keys = {
            "api_credentials",
            "channel_pairs",
            "replacement_rules",
            "filters",
            "settings",
            "workers"
        }
        return any(key in full_config for key in legacy_keys)

    def _init_db(self) -> None:
        """Initialize SQLite schema."""
        if not self.db_path:
            return
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workers (
                    worker_id TEXT PRIMARY KEY,
                    api_id INTEGER,
                    api_hash TEXT,
                    session_name TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id TEXT NOT NULL,
                    source INTEGER NOT NULL,
                    target INTEGER NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    backfill_count INTEGER NOT NULL DEFAULT 10,
                    FOREIGN KEY(worker_id) REFERENCES workers(worker_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS replacement_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id TEXT NOT NULL,
                    find_text TEXT NOT NULL,
                    replace_text TEXT NOT NULL,
                    case_sensitive INTEGER NOT NULL DEFAULT 0,
                    is_regex INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(worker_id) REFERENCES workers(worker_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS filters (
                    worker_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    mode TEXT NOT NULL DEFAULT 'whitelist',
                    keywords_json TEXT NOT NULL DEFAULT '[]',
                    FOREIGN KEY(worker_id) REFERENCES workers(worker_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    worker_id TEXT PRIMARY KEY,
                    retry_attempts INTEGER NOT NULL DEFAULT 5,
                    retry_delay INTEGER NOT NULL DEFAULT 5,
                    flood_wait_extra_delay INTEGER NOT NULL DEFAULT 10,
                    max_message_length INTEGER NOT NULL DEFAULT 4096,
                    log_level TEXT NOT NULL DEFAULT 'INFO',
                    add_source_link INTEGER NOT NULL DEFAULT 0,
                    source_link_text TEXT NOT NULL DEFAULT '\n\n🔗 Source: {link}',
                    FOREIGN KEY(worker_id) REFERENCES workers(worker_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _open_db(self) -> sqlite3.Connection:
        """Open a SQLite connection with foreign keys enabled."""
        if not self.db_path:
            raise RuntimeError("Database path not set")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _normalize_filters(self, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize filter config with defaults."""
        normalized = dict(DEFAULT_FILTERS)
        if filters:
            normalized.update(filters)
        keywords = normalized.get("keywords", [])
        if not isinstance(keywords, list):
            normalized["keywords"] = []
        return normalized

    def _normalize_settings(self, settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize settings config with defaults."""
        normalized = dict(DEFAULT_SETTINGS)
        if settings:
            normalized.update(settings)
        return normalized

    def _write_db_from_config(self, config: Dict[str, Any]) -> None:
        """Persist config dict to SQLite."""
        if not self.db_path:
            return

        mode = "multi" if isinstance(config.get("workers"), list) else "single"
        self._config_mode = mode

        if mode == "multi":
            workers = config.get("workers", [])
        else:
            api_credentials = config.get("api_credentials", {})
            workers = [{
                "worker_id": DEFAULT_WORKER_ID,
                "api_id": api_credentials.get("api_id", DEFAULT_API_CREDENTIALS["api_id"]),
                "api_hash": api_credentials.get("api_hash", DEFAULT_API_CREDENTIALS["api_hash"]),
                "session_name": api_credentials.get("session_name", DEFAULT_API_CREDENTIALS["session_name"]),
                "enabled": True,
                "channel_pairs": config.get("channel_pairs", []),
                "replacement_rules": config.get("replacement_rules", []),
                "filters": config.get("filters", {}),
                "settings": config.get("settings", {})
            }]

        conn = self._open_db()
        try:
            conn.execute("BEGIN")
            conn.execute("DELETE FROM channel_pairs")
            conn.execute("DELETE FROM replacement_rules")
            conn.execute("DELETE FROM filters")
            conn.execute("DELETE FROM settings")
            conn.execute("DELETE FROM workers")

            for worker in workers:
                worker_id = worker.get("worker_id", DEFAULT_WORKER_ID)
                api_id = worker.get("api_id", DEFAULT_API_CREDENTIALS["api_id"])
                api_hash = worker.get("api_hash", DEFAULT_API_CREDENTIALS["api_hash"])
                session_name = worker.get("session_name", DEFAULT_API_CREDENTIALS["session_name"])
                enabled = 1 if worker.get("enabled", True) else 0

                conn.execute(
                    """
                    INSERT INTO workers (worker_id, api_id, api_hash, session_name, enabled)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (worker_id, api_id, api_hash, session_name, enabled)
                )

                for pair in worker.get("channel_pairs", []):
                    conn.execute(
                        """
                        INSERT INTO channel_pairs (worker_id, source, target, enabled, backfill_count)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            worker_id,
                            pair.get("source"),
                            pair.get("target"),
                            1 if pair.get("enabled", True) else 0,
                            pair.get("backfill_count", 10)
                        )
                    )

                for rule in worker.get("replacement_rules", []):
                    conn.execute(
                        """
                        INSERT INTO replacement_rules (worker_id, find_text, replace_text, case_sensitive, is_regex)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            worker_id,
                            rule.get("find", ""),
                            rule.get("replace", ""),
                            1 if rule.get("case_sensitive", False) else 0,
                            1 if rule.get("is_regex", False) else 0
                        )
                    )

                filters = self._normalize_filters(worker.get("filters"))
                conn.execute(
                    """
                    INSERT INTO filters (worker_id, enabled, mode, keywords_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        worker_id,
                        1 if filters.get("enabled", False) else 0,
                        filters.get("mode", "whitelist"),
                        json.dumps(filters.get("keywords", []))
                    )
                )

                settings = self._normalize_settings(worker.get("settings"))
                conn.execute(
                    """
                    INSERT INTO settings (
                        worker_id, retry_attempts, retry_delay, flood_wait_extra_delay,
                        max_message_length, log_level, add_source_link, source_link_text
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        worker_id,
                        settings.get("retry_attempts", 5),
                        settings.get("retry_delay", 5),
                        settings.get("flood_wait_extra_delay", 10),
                        settings.get("max_message_length", 4096),
                        settings.get("log_level", "INFO"),
                        1 if settings.get("add_source_link", False) else 0,
                        settings.get("source_link_text", DEFAULT_SETTINGS["source_link_text"])
                    )
                )

            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("config_mode", mode)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _build_config_from_db(self, admin_config: Dict[str, Any]) -> Dict[str, Any]:
        """Rebuild config dict from SQLite and admin JSON."""
        config: Dict[str, Any] = {
            "admin_bot_token": admin_config.get("admin_bot_token", ""),
            "admin_user_ids": admin_config.get("admin_user_ids", [])
        }

        if not self.db_path or not os.path.exists(self.db_path):
            config.update({
                "api_credentials": dict(DEFAULT_API_CREDENTIALS),
                "channel_pairs": [],
                "replacement_rules": [],
                "filters": dict(DEFAULT_FILTERS),
                "settings": dict(DEFAULT_SETTINGS)
            })
            self._config_mode = "single"
            return config

        conn = self._open_db()
        try:
            mode_row = conn.execute(
                "SELECT value FROM meta WHERE key = ?",
                ("config_mode",)
            ).fetchone()
            mode = mode_row["value"] if mode_row else "single"
            self._config_mode = mode

            worker_rows = conn.execute(
                "SELECT worker_id, api_id, api_hash, session_name, enabled FROM workers ORDER BY rowid"
            ).fetchall()

            workers: List[Dict[str, Any]] = []
            for row in worker_rows:
                worker_id = row["worker_id"]
                pairs_rows = conn.execute(
                    """
                    SELECT source, target, enabled, backfill_count
                    FROM channel_pairs
                    WHERE worker_id = ?
                    ORDER BY id
                    """,
                    (worker_id,)
                ).fetchall()
                rules_rows = conn.execute(
                    """
                    SELECT find_text, replace_text, case_sensitive, is_regex
                    FROM replacement_rules
                    WHERE worker_id = ?
                    ORDER BY id
                    """,
                    (worker_id,)
                ).fetchall()
                filter_row = conn.execute(
                    """
                    SELECT enabled, mode, keywords_json
                    FROM filters
                    WHERE worker_id = ?
                    """,
                    (worker_id,)
                ).fetchone()
                settings_row = conn.execute(
                    """
                    SELECT retry_attempts, retry_delay, flood_wait_extra_delay,
                           max_message_length, log_level, add_source_link, source_link_text
                    FROM settings
                    WHERE worker_id = ?
                    """,
                    (worker_id,)
                ).fetchone()

                filters = dict(DEFAULT_FILTERS)
                if filter_row:
                    filters.update({
                        "enabled": bool(filter_row["enabled"]),
                        "mode": filter_row["mode"],
                        "keywords": json.loads(filter_row["keywords_json"]) if filter_row["keywords_json"] else []
                    })

                settings = dict(DEFAULT_SETTINGS)
                if settings_row:
                    settings.update({
                        "retry_attempts": settings_row["retry_attempts"],
                        "retry_delay": settings_row["retry_delay"],
                        "flood_wait_extra_delay": settings_row["flood_wait_extra_delay"],
                        "max_message_length": settings_row["max_message_length"],
                        "log_level": settings_row["log_level"],
                        "add_source_link": bool(settings_row["add_source_link"]),
                        "source_link_text": settings_row["source_link_text"]
                    })

                worker = {
                    "worker_id": worker_id,
                    "api_id": row["api_id"],
                    "api_hash": row["api_hash"],
                    "session_name": row["session_name"],
                    "enabled": bool(row["enabled"]),
                    "channel_pairs": [
                        {
                            "source": pair["source"],
                            "target": pair["target"],
                            "enabled": bool(pair["enabled"]),
                            "backfill_count": pair["backfill_count"]
                        }
                        for pair in pairs_rows
                    ],
                    "replacement_rules": [
                        {
                            "find": rule["find_text"],
                            "replace": rule["replace_text"],
                            "case_sensitive": bool(rule["case_sensitive"]),
                            "is_regex": bool(rule["is_regex"])
                        }
                        for rule in rules_rows
                    ],
                    "filters": filters,
                    "settings": settings
                }
                workers.append(worker)

            if mode == "multi":
                config["workers"] = workers
            else:
                worker = workers[0] if workers else {
                    "worker_id": DEFAULT_WORKER_ID,
                    "api_id": DEFAULT_API_CREDENTIALS["api_id"],
                    "api_hash": DEFAULT_API_CREDENTIALS["api_hash"],
                    "session_name": DEFAULT_API_CREDENTIALS["session_name"],
                    "enabled": True,
                    "channel_pairs": [],
                    "replacement_rules": [],
                    "filters": dict(DEFAULT_FILTERS),
                    "settings": dict(DEFAULT_SETTINGS)
                }
                config.update({
                    "api_credentials": {
                        "api_id": worker.get("api_id", DEFAULT_API_CREDENTIALS["api_id"]),
                        "api_hash": worker.get("api_hash", DEFAULT_API_CREDENTIALS["api_hash"]),
                        "session_name": worker.get("session_name", DEFAULT_API_CREDENTIALS["session_name"])
                    },
                    "channel_pairs": worker.get("channel_pairs", []),
                    "replacement_rules": worker.get("replacement_rules", []),
                    "filters": worker.get("filters", dict(DEFAULT_FILTERS)),
                    "settings": worker.get("settings", dict(DEFAULT_SETTINGS))
                })
        finally:
            conn.close()

        return config

    def get_storage_mtime(self) -> float:
        """Get storage modification time (SQLite preferred)."""
        if self.db_path and os.path.exists(self.db_path):
            return os.path.getmtime(self.db_path)
        if self.config_path and os.path.exists(self.config_path):
            return os.path.getmtime(self.config_path)
        return 0

    def is_multi_worker_mode(self) -> bool:
        """Check if config is in multi-worker mode."""
        return "workers" in self.config or self._config_mode == "multi"

    def get_api_credentials(self) -> Dict[str, Any]:
        """Get API credentials."""
        return self.config.get("api_credentials", {})

    def get_channel_pairs(self) -> List[Dict[str, Any]]:
        """Get list of enabled channel pairs."""
        if self.is_multi_worker_mode():
            all_pairs = []
            for worker in self.config.get("workers", []):
                if worker.get("enabled", True):
                    pairs = worker.get("channel_pairs", [])
                    all_pairs.extend([p for p in pairs if p.get("enabled", True)])
            return all_pairs
        pairs = self.config.get("channel_pairs", [])
        return [pair for pair in pairs if pair.get("enabled", True)]

    def get_all_channel_pairs(self) -> List[Dict[str, Any]]:
        """Get all channel pairs including disabled ones."""
        if self.is_multi_worker_mode():
            all_pairs = []
            for worker in self.config.get("workers", []):
                all_pairs.extend(worker.get("channel_pairs", []))
            return all_pairs
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
                    target_worker = None
                    if worker_id:
                        for worker in workers:
                            if worker.get("worker_id") == worker_id:
                                target_worker = worker
                                break
                    if not target_worker:
                        target_worker = workers[0]
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
            all_rules = []
            for worker in self.config.get("workers", []):
                if worker.get("enabled", True):
                    rules = worker.get("replacement_rules", [])
                    all_rules.extend(rules)
            return all_rules
        return self.config.get("replacement_rules", [])

    def add_replacement_rule(self, find: str, replace: str, case_sensitive: bool = False, is_regex: bool = False,
                             worker_id: str = None) -> None:
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
                workers = self.config.get("workers", [])
                for worker in workers:
                    if worker_id is None or worker.get("worker_id") == worker_id:
                        worker.setdefault("replacement_rules", []).append(rule)
            else:
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
