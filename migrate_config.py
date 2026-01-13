#!/usr/bin/env python3
"""Force config migration from JSON to SQLite without starting the bot."""
from src.config_manager import ConfigManager


def main() -> None:
    config_manager = ConfigManager()
    config = config_manager.load()

    mode = "multi" if "workers" in config else "single"
    db_path = config_manager.db_path

    print("✅ Config loaded")
    print(f"Mode: {mode}")
    print(f"SQLite DB: {db_path}")


if __name__ == "__main__":
    main()
