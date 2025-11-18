"""Worker Manager for multi-process forwarding with separate API credentials."""
import asyncio
import json
import multiprocessing
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging

from bot import TelegramForwarder
from src.logger_setup import setup_logger


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
    try:
        # Create a custom config file for this worker
        worker_config_path = f"worker_{worker_id}_config.json"
        
        # Build worker-specific config
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
        
        # Save worker config
        with open(worker_config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Run the forwarder bot
        bot = TelegramForwarder(worker_config_path)
        asyncio.run(bot.start())
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger = logging.getLogger(f"Worker-{worker_id}")
        logger.error(f"Worker {worker_id} crashed: {e}")
        raise


class WorkerManager:
    """Manages multiple worker processes."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.workers: Dict[str, WorkerProcess] = {}
        self.logger = setup_logger("WorkerManager", log_file="logs/worker_manager.log")
        self.running = False
        
    def load_workers_from_config(self):
        """Load worker configurations from config file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            workers_config = config.get("workers", [])
            
            # Clear existing workers
            self.workers.clear()
            
            # Create worker objects
            for worker_cfg in workers_config:
                if worker_cfg.get("enabled", True):
                    worker_id = worker_cfg["worker_id"]
                    self.workers[worker_id] = WorkerProcess(worker_id, worker_cfg)
                    self.logger.info(f"✓ Loaded worker config: {worker_id}")
            
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
        """Monitor worker health and restart if needed."""
        while self.running:
            try:
                for worker_id, worker in list(self.workers.items()):
                    if not worker.is_alive():
                        self.logger.warning(
                            f"⚠️ Worker {worker_id} is dead (restarts: {worker.restart_count})"
                        )
                        
                        # Auto-restart if not too many restarts
                        if worker.restart_count < 5:
                            self.logger.info(f"🔄 Restarting worker {worker_id}...")
                            worker.restart()
                        else:
                            self.logger.error(
                                f"❌ Worker {worker_id} failed too many times, not restarting"
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
                self.logger.warning("⚠️ No workers configured. Please add workers to config.json")
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

