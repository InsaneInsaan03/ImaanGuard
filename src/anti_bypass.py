import os
import time
import psutil
import subprocess
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [Watchdog.%(funcName)s]: %(message)s",
    handlers=[logging.StreamHandler()]
)

class Watchdog:
    def __init__(self, target_process: str = "python.exe", target_script: Optional[str] = "main.py", target_exe: Optional[str] = None):
        """
        Initialize the watchdog to monitor and restart the main ImaanGuard process.
        
        Args:
            target_process: Name of the process to monitor (e.g., 'python.exe' or 'ImaanGuard.exe').
            target_script: Script to relaunch if using Python (e.g., 'main.py').
            target_exe: Path to executable if bundled (e.g., 'dist/ImaanGuard.exe').
        """
        logging.debug("Initializing watchdog")
        self.target_process = target_process.lower()
        self.target_script = target_script
        self.target_exe = target_exe
        self.running = False
        self.target_pid = None
        logging.info("Watchdog initialized")

    def start(self):
        """
        Start the watchdog monitoring loop.
        """
        logging.info("Starting watchdog")
        self.running = True
        try:
            while self.running:
                if not self._is_target_running():
                    logging.warning("Target process not running, attempting restart")
                    self._restart_target()
                time.sleep(5)  # Check every 5 seconds
        except KeyboardInterrupt:
            logging.info("Watchdog interrupted, stopping")
            self.stop()
        except Exception as e:
            logging.error(f"Error in watchdog loop: {e}")

    def stop(self):
        """
        Stop the watchdog.
        """
        logging.info("Stopping watchdog")
        self.running = False

    def _is_target_running(self) -> bool:
        """
        Check if the target process is running.
        
        Returns:
            bool: True if target process is running, False otherwise.
        """
        logging.debug(f"Checking if {self.target_process} is running")
        try:
            for proc in psutil.process_iter(['name', 'pid', 'cmdline']):
                proc_name = proc.info['name'].lower()
                if proc_name != self.target_process:
                    continue
                # For Python, verify it's running the target script
                if self.target_script and self.target_process == "python.exe":
                    cmdline = proc.info.get('cmdline', [])
                    if not any(self.target_script in arg for arg in cmdline):
                        continue
                # For .exe, verify it's the target executable
                if self.target_exe:
                    cmdline = proc.info.get('cmdline', [])
                    if not any(self.target_exe in arg for arg in cmdline):
                        continue
                self.target_pid = proc.info['pid']
                logging.debug(f"Target process found, PID: {self.target_pid}")
                return True
            logging.debug("Target process not found")
            self.target_pid = None
            return False
        except psutil.Error as e:
            logging.error(f"Error checking target process: {e}")
            return False

    def _restart_target(self):
        """
        Restart the target process.
        """
        logging.debug("Attempting to restart target process")
        try:
            if self.target_exe:
                # Launch .exe
                subprocess.Popen([self.target_exe], creationflags=subprocess.DETACHED_PROCESS)
                logging.info(f"Restarted {self.target_exe}")
            elif self.target_script:
                # Launch Python script
                subprocess.Popen(["python", self.target_script], creationflags=subprocess.DETACHED_PROCESS)
                logging.info(f"Restarted {self.target_script}")
            else:
                logging.error("No target executable or script specified")
            # Wait briefly to confirm restart
            time.sleep(2)
            if self._is_target_running():
                logging.info("Target process successfully restarted")
            else:
                logging.warning("Failed to restart target process")
        except (subprocess.SubprocessError, OSError) as e:
            logging.error(f"Error restarting target process: {e}")

def main():
    """
    Test the watchdog.
    """
    logging.info("Starting watchdog test")
    watchdog = Watchdog(target_process="Python.exe", target_script="main.py")
    watchdog.start()

if __name__ == "__main__":
    main()