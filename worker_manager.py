"""Worker Manager for multi-process forwarding with separate API credentials."""
import asyncio
import multiprocessing
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging

from bot import TelegramForwarder
from src.logger_setup import setup_logger
from src.config_manager import ConfigManager


class WorkerProcess:
    """Represents a single worker process with its own API credentials."""
    
    def __init__(self, worker_id: str, worker_config: Dict):
        self.worker_id = worker_id
        self.config = worker_config
        self.process: Optional[multiprocessing.Process] = None
        self.start_time: Optional[float] = None
        self.restart_count = 0
        
    def is_alive(self) -> bool:
        """Check if worker process is running."""
        return self.process is not None and self.process.is_alive()
    
    def start(self):
        """Start the worker process."""
        self.process = multiprocessing.Process(
            target=run_worker,
            args=(self.worker_id, self.config),
            name=f"Worker-{self.worker_id}"
        )
        self.process.start()
        self.start_time = time.time()
        
    def stop(self, timeout: int = 10):
        """Stop the worker process gracefully."""
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=timeout)
            if self.process.is_alive():
                self.process.kill()
                self.process.join()
    
    def restart(self):
        """Restart the worker process."""
        self.stop()
        self.restart_count += 1
        time.sleep(2)  # Brief delay before restart
        self.start()


def run_worker(worker_id: str, worker_config: Dict):
    """Run a single worker in its own process."""
    logger = None
    try:
        # Set up logger for this worker
        from src.logger_setup import setup_logger
        logger = setup_logger(f"Worker-{worker_id}", log_file=f"logs/worker_{worker_id}.log")
        logger.info(f"=" * 60)
        logger.info(f"🚀 Starting worker: {worker_id}")
        logger.info(f"=" * 60)
        
        # Build worker-specific config dict (no file needed!)
        config_data = {
            "api_credentials": {
                "api_id": worker_config["api_id"],
                "api_hash": worker_config["api_hash"],
                "session_name": worker_config["session_name"]
            },
            "channel_pairs": worker_config.get("channel_pairs", []),
            "replacement_rules": worker_config.get("replacement_rules", []),
            "filters": worker_config.get("filters", {
                "enabled": False,
                "mode": "whitelist",
                "keywords": []
            }),
            "settings": worker_config.get("settings", {
                "retry_attempts": 5,
                "retry_delay": 5,
                "flood_wait_extra_delay": 10,
                "max_message_length": 4096,
                "log_level": "INFO",
                "add_source_link": False,
                "source_link_text": "\n\n🔗 Source: {link}"
            })
        }
        
        # Run the forwarder bot with config dict directly (no file created!)
        # CRITICAL: Explicitly create and set event loop for subprocess
        # asyncio.run() doesn't work well with Telethon in multiprocessing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        bot = TelegramForwarder(config_data)
        
        try:
            loop.run_until_complete(bot.start())
        finally:
            loop.close()
        
    except KeyboardInterrupt:
        if logger:
            logger.info("Worker stopped by user")
        pass
    except RuntimeError as e:
        # Handle database lock errors specifically
        error_msg = str(e).lower()
        if "database is locked" in error_msg or "session database is locked" in error_msg:
            if logger:
                logger.error(
                    f"❌ Worker {worker_id} failed: Database lock error\n"
                    f"This usually means:\n"
                    f"1. Another process is using the same session file\n"
                    f"2. A previous crash left the database locked\n"
                    f"3. Multiple workers are sharing the same session_name\n\n"
                    f"Solution: Stop all workers, wait 1-2 minutes, then restart."
                )
            # Don't re-raise, let the worker manager handle restart logic
            return
        else:
            if logger:
                logger.error(f"Worker {worker_id} crashed: {e}")
            raise
    except Exception as e:
        if logger:
            logger.error(f"Worker {worker_id} crashed: {e}", exc_info=True)
        raise


class WorkerManager:
    """Manages multiple worker processes."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.workers: Dict[str, WorkerProcess] = {}
        self.logger = setup_logger("WorkerManager", log_file="logs/worker_manager.log")
        self.running = False
        self.config_manager = ConfigManager(self.config_path)
        self.config_mtime = self._get_config_mtime()
        self.last_config_check = time.time()
        self.worker_configs: Dict[str, Dict] = {}  # Store original worker configs
        
    def _get_config_mtime(self) -> float:
        """Get config storage modification time."""
        try:
            return self.config_manager.get_storage_mtime()
        except Exception:
            return 0
    
    def _configs_equal(self, config1: Dict, config2: Dict) -> bool:
        """Compare two worker configs (ignoring restart_count and runtime data)."""
        import json
        # Compare only the important parts
        relevant_keys = ["api_id", "api_hash", "session_name", "channel_pairs", "replacement_rules", "filters", "settings"]
        c1 = {k: config1.get(k) for k in relevant_keys if k in config1}
        c2 = {k: config2.get(k) for k in relevant_keys if k in config2}
        return json.dumps(c1, sort_keys=True) == json.dumps(c2, sort_keys=True)
    
    def load_workers_from_config(self, restart_on_change: bool = False):
        """
        Load worker configurations from config file.
        
        Args:
            restart_on_change: If True, restart workers whose config has changed
        """
        try:
            config = self.config_manager.load()
            
            workers_config = config.get("workers", [])
            new_worker_configs = {}
            
            # Build dict of new configs
            for worker_cfg in workers_config:
                if worker_cfg.get("enabled", True):
                    worker_id = worker_cfg["worker_id"]
                    new_worker_configs[worker_id] = worker_cfg
            
            # Check for changes if restart_on_change is True
            if restart_on_change:
                for worker_id, new_cfg in new_worker_configs.items():
                    old_cfg = self.worker_configs.get(worker_id)
                    
                    if worker_id not in self.workers:
                        # New worker - create and start it
                        self.logger.info(f"🆕 New worker detected: {worker_id}")
                        worker = WorkerProcess(worker_id, new_cfg)
                        self.workers[worker_id] = worker
                        worker.start()
                        self.logger.info(f"✅ Worker {worker_id} started (PID: {worker.process.pid})")
                    elif old_cfg and not self._configs_equal(old_cfg, new_cfg):
                        # Config changed - restart worker
                        self.logger.info(f"🔄 Config changed for worker {worker_id} - restarting...")
                        old_worker = self.workers[worker_id]
                        old_worker.stop()
                        
                        # Create new worker with updated config
                        new_worker = WorkerProcess(worker_id, new_cfg)
                        new_worker.restart_count = old_worker.restart_count  # Preserve restart count
                        self.workers[worker_id] = new_worker
                        new_worker.start()
                        self.logger.info(f"✅ Worker {worker_id} restarted with new config (PID: {new_worker.process.pid})")
                
                # Check for removed workers
                for worker_id in list(self.workers.keys()):
                    if worker_id not in new_worker_configs:
                        self.logger.info(f"🗑️  Worker {worker_id} removed from config - stopping...")
                        self.workers[worker_id].stop()
                        del self.workers[worker_id]
            else:
                # Initial load - just create workers
                self.workers.clear()
                for worker_id, worker_cfg in new_worker_configs.items():
                    self.workers[worker_id] = WorkerProcess(worker_id, worker_cfg)
                    self.logger.info(f"✓ Loaded worker config: {worker_id}")
            
            # Store current configs
            self.worker_configs = new_worker_configs
            
            self.logger.info(f"Loaded {len(self.workers)} worker(s) from config")
            
        except Exception as e:
            self.logger.error(f"Failed to load worker config: {e}")
            raise
    
    def start_all_workers(self):
        """Start all configured workers."""
        self.logger.info(f"🚀 Starting {len(self.workers)} worker(s)...")
        
        for worker_id, worker in self.workers.items():
            try:
                worker.start()
                self.logger.info(f"✅ Worker {worker_id} started (PID: {worker.process.pid})")
            except Exception as e:
                self.logger.error(f"❌ Failed to start worker {worker_id}: {e}")
    
    def stop_all_workers(self):
        """Stop all running workers."""
        self.logger.info(f"🛑 Stopping {len(self.workers)} worker(s)...")
        
        for worker_id, worker in self.workers.items():
            try:
                worker.stop()
                self.logger.info(f"✅ Worker {worker_id} stopped")
            except Exception as e:
                self.logger.error(f"❌ Error stopping worker {worker_id}: {e}")
    
    def monitor_workers(self):
        """Monitor worker health and restart if needed. Also check for config changes."""
        while self.running:
            try:
                # Check for config file changes every 2 minutes
                current_time = time.time()
                if current_time - self.last_config_check >= 120:  # 120 seconds = 2 minutes
                    self.last_config_check = current_time
                    current_mtime = self._get_config_mtime()
                    
                    if current_mtime > self.config_mtime:
                        self.logger.info("🔄 Config file modified - checking for changes...")
                        self.config_mtime = current_mtime
                        
                        try:
                            # Reload config and restart workers if needed
                            self.load_workers_from_config(restart_on_change=True)
                            self.logger.info("✅ Config reload complete")
                        except Exception as e:
                            self.logger.error(f"❌ Failed to reload config: {e}")
                
                # Check worker health
                for worker_id, worker in list(self.workers.items()):
                    if not worker.is_alive():
                        self.logger.warning(
                            f"⚠️ Worker {worker_id} is dead (restarts: {worker.restart_count})"
                        )
                        
                        # Check if worker exited due to database lock
                        # (This is a heuristic - we check if it crashed quickly)
                        if worker.start_time and (time.time() - worker.start_time) < 10:
                            self.logger.warning(
                                f"⚠️ Worker {worker_id} crashed quickly - possible database lock issue. "
                                f"Waiting 30 seconds before restart to allow lock to clear..."
                            )
                            time.sleep(30)  # Wait longer for database lock to clear
                        
                        # Auto-restart if not too many restarts
                        if worker.restart_count < 5:
                            self.logger.info(f"🔄 Restarting worker {worker_id}...")
                            worker.restart()
                        else:
                            self.logger.error(
                                f"❌ Worker {worker_id} failed too many times, not restarting. "
                                f"This may be due to a persistent database lock. "
                                f"Please stop all workers, wait 1-2 minutes, then manually restart."
                            )
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                time.sleep(5)
    
    def get_status(self) -> Dict:
        """Get status of all workers."""
        status = {}
        for worker_id, worker in self.workers.items():
            status[worker_id] = {
                "alive": worker.is_alive(),
                "pid": worker.process.pid if worker.process else None,
                "uptime": time.time() - worker.start_time if worker.start_time else 0,
                "restart_count": worker.restart_count
            }
        return status
    
    def run(self):
        """Run the worker manager."""
        try:
            self.logger.info("=" * 60)
            self.logger.info("🎯 Multi-Worker Telegram Forwarder Manager")
            self.logger.info("=" * 60)
            
            # Load config
            self.load_workers_from_config()
            
            if not self.workers:
                self.logger.warning("⚠️ No workers configured. Please add workers to config.db via admin bot/panel.")
                return
            
            # Start all workers
            self.start_all_workers()
            
            # Start monitoring
            self.running = True
            self.logger.info("👀 Starting worker monitor...")
            self.monitor_workers()
            
        except KeyboardInterrupt:
            self.logger.info("\n⚠️ Shutdown signal received")
        finally:
            self.running = False
            self.stop_all_workers()
            self.logger.info("✅ Worker Manager stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n⚠️ Received shutdown signal, stopping workers...")
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run manager
    manager = WorkerManager()
    manager.run()
