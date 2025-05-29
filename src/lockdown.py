import os
import time
import json
import psutil
import threading
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import shutil
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [Lockdown.%(funcName)s]: %(message)s",
    handlers=[logging.StreamHandler()]
)

class Lockdown:
    def __init__(self, lock_file: str = "data/lockdown.json"):
        """
        Initialize the lockdown manager.
        
        Args:
            lock_file: Path to session state file.
        """
        logging.debug("Initializing lockdown manager")
        self.lock_file = lock_file
        self.is_locked = False
        self.lock_end_time = 0
        self.lock_duration = 0
        self.violation_count = 1  # Start with first violation
        self.last_violation_time = None  # Track last violation timestamp
        self.ENABLE_CACHE_NUKE = False  # Set to True in production
        self.is_bypass = False
        self._lock_thread = None
        self._stop_event = threading.Event()
        self._killed_pids = set()  # Track killed PIDs to avoid redundant kills
        logging.info("Lockdown manager initialized")
        
        # Start daily violation decay check
        self._start_daily_decay_check()

    def _start_daily_decay_check(self):
        """
        Start a thread to run check_violation_decay daily.
        """
        def run_daily_check():
            while not self._stop_event.is_set():
                self.check_violation_decay()
                time.sleep(86400)  # Wait 24 hours
        decay_thread = threading.Thread(target=run_daily_check, daemon=True)
        decay_thread.start()
        logging.debug("Daily violation decay check thread started")

    def lock_system(self, duration: Optional[int] = None, is_bypass: bool = False):
        """
        Enforce lockdown in a background thread.
        
        Args:
            duration: Lock duration in seconds (optional, calculated if None).
            is_bypass: True if triggered by bypass attempt (2-day lock).
        """
        logging.info(f"Locking system (Bypass: {is_bypass}, Violation count: {self.violation_count})")
        
        # Calculate duration if not provided
        if is_bypass:
            duration = 300  # 2 days for bypass
        elif duration is None:
            durations = [30, 60, 120, 240]  # 2h, 4h, 8h, 16h
            duration = durations[min(self.violation_count - 1, len(durations) - 1)] if self.violation_count <= 4 else 86400  # Cap at 24h
        
        self.is_locked = True
        self.lock_duration = duration
        self.lock_end_time = time.time() + duration
        self.is_bypass = is_bypass
        self._killed_pids = set()
        self._stop_event.clear()
        
        # Increment violation count and reset 7-day clock (not for bypass)
        if not is_bypass:
            self.violation_count += 1
            self.last_violation_time = datetime.now()  # Reset 7-day clock
            logging.info("Violation detected, 7-day clean streak reset")
        
        # Save lock state
        logging.info(f"------------------------------------------[DEBUG] [KeyboardMonitor.trigger_lockdown]: Triggering lockdown for {duration} seconds")
        self._save_lock_state()
        
        # Log event
        logging.debug("Logging lockdown event (TODO: logger.py)")
        
        # Check if lockdown thread is already running and alive
        if self._lock_thread is not None and self._lock_thread.is_alive():
            logging.info("Lockdown thread already running, not starting a new one")
        else:
            # Start lockdown in background thread
            self._lock_thread = threading.Thread(target=self._lock_loop, daemon=True)
            self._lock_thread.start()
            logging.info("Lockdown thread started")

    def _lock_loop(self):
        """
        Background loop to enforce lockdown restrictions.
        """
        logging.debug("Starting lockdown loop")
        self._disable_internet()
        try:
            while time.time() < self.lock_end_time and self.is_locked and not self._stop_event.is_set():
                self._enforce_restrictions()
                time.sleep(1)  # Check every 1 second
        except Exception as e:
            logging.error(f"Error in lockdown loop: {e}")
        finally:
            if time.time() >= self.lock_end_time or self._stop_event.is_set():
                self.unlock_system()

    def _enforce_restrictions(self):
        """
        Enforce explorer.exe, tools, and network process restrictions.
        """
        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                # executor.submit(self._kill_explorer)
                # executor.submit(self._block_tools)
                executor.submit(self._kill_network_processes)
                # executor.submit(self.shutdown_system)
        except Exception as e:
            logging.error(f"Error enforcing restrictions: {e}")

    def check_and_reapply_lock(self):
        """
        Check lock state on boot and reapply if lockdown is still active.
        """
        logging.info("Checking lock state on boot")
        try:
            with open(self.lock_file, 'r') as f:
                state = json.load(f)
            if state.get('is_locked', False) and time.time() < state.get('lock_end_time', 0):
                self.violation_count = state.get('violation_count', 1)  # Restore or default to 1
                self.last_violation_time = datetime.fromisoformat(state.get('last_violation_time', None)) if state.get('last_violation_time') else None
                remaining_duration = state['lock_end_time'] - time.time()
                logging.info(f"Reapplying lock for {remaining_duration} seconds, violation count: {self.violation_count}")
                self.lock_system(max(0, int(remaining_duration)), is_bypass=state.get('is_bypass', False))
            else:
                logging.info("No active lock or lock expired")
                self._clear_lock_state()  # Clear lock file but preserve violation_count
                self.check_violation_decay()  # Check for decay after lock expires
        except FileNotFoundError:
            logging.debug("No lock file found, assuming fresh start")
            self.violation_count = 1  # Reset only for fresh start
            self.last_violation_time = None
        except Exception as e:
            logging.error(f"Error checking lock state: {e}")

    def check_violation_decay(self):
        """
        Decrease violation count to 1 if no violations for 7 days.
        """
        if self.violation_count > 1 and self.last_violation_time:
            now = datetime.now()
            days_since_violation = (now - self.last_violation_time).days
            if days_since_violation >= 7:
                logging.info("7 clean days! Decreasing violation count to 1")
                self.violation_count = 1
                self.last_violation_time = None  # Reset violation time
                self._save_lock_state()

    def _save_lock_state(self):
        """
        Save lock state to lockdown.json.
        """
        logging.debug("Saving lock state")
        try:
            state = {
                'is_locked': self.is_locked,
                'lock_start_time': time.time(),
                'lock_end_time': self.lock_end_time,
                'lock_duration': self.lock_duration,
                'is_bypass': self.is_bypass,
                'violation_count': self.violation_count,
                'last_violation_time': self.last_violation_time.isoformat() if self.last_violation_time else None
            }
            os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
            with open(self.lock_file, 'w') as f:
                json.dump(state, f)
            logging.info("Lock state saved")
        except Exception as e:
            logging.error(f"Error saving lock state: {e}")

    def _clear_lock_state(self):
        """
        Clear lock state from lockdown.json.
        """
        logging.debug("Clearing lock state")
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
                logging.info("Lock state cleared")
        except Exception as e:
            logging.error(f"Error clearing lock state: {e}")
    
    def shutdown_system(self):
        """
        Shutdown the system immediately.
        """
        logging.info("Initiating system shutdown")
        try:
            os.system("shutdown /s /t 0")
        except Exception as e:
            logging.error(f"Failed to shutdown system: {e}")

    def _kill_explorer(self):
        """
        Kill explorer.exe if running and not already killed.
        """
        logging.debug("Checking for explorer.exe")
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                proc_name = proc.info['name']
                if proc_name and proc_name.lower() == 'explorer.exe':
                    if proc.pid not in self._killed_pids:
                        logging.info(f"Killing explorer.exe (PID: {proc.pid})")
                        proc.kill()
                        self._killed_pids.add(proc.pid)
                    else:
                        logging.debug("explorer.exe already killed, skipping")
                    break  # No need to scan further
        except psutil.Error as e:
            logging.error(f"Error killing explorer.exe: {e}")

    def _block_tools(self):
        """
        Block Task Manager and shell processes if newly spawned.
        """
        logging.debug("Checking for Task Manager and shells")
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                proc_name = proc.info['name'].lower()
                if proc_name in ['taskmgr.exe', 'cmd.exe', 'powershell.exe'] and proc.pid not in self._killed_pids:
                    logging.info(f"Killing {proc_name}")
                    proc.kill()
                    self._killed_pids.add(proc.pid)
        except psutil.Error as e:
            logging.error(f"Error blocking tools: {e}")

    def _disable_internet(self):
        """
        Disable all network adapters and block internet with firewall.
        """
        logging.debug("Disabling internet")
        try:
            # Disable network adapters
            os.system('netsh interface set interface "Wi-Fi" admin=disable')
            os.system('netsh interface set interface "Ethernet" admin=disable')
            logging.info("Network adapters disabled")

            # Add firewall rule
            os.system('netsh advfirewall firewall add rule name="LockdownBlockAll" dir=in action=block enable=yes')
            os.system('netsh advfirewall firewall add rule name="LockdownBlockAll" dir=out action=block enable=yes')
            logging.info("Firewall rules added")
        except Exception as e:
            logging.error(f"Error disabling internet: {e}")

    def _clear_browser_cache(self, browser_name):
        """
        Clear cache folders for supported browsers.
        """
        try:
            user_profile = os.getenv('USERPROFILE')
            if browser_name == 'chrome.exe':
                cache_path = os.path.join(user_profile, r'AppData\\Local\\Google\\Chrome\\User Data\\Default')
            elif browser_name == 'firefox.exe':
                cache_path = os.path.join(user_profile, r'AppData\\Local\\Mozilla\\Firefox\\Profiles')
                # Firefox profiles folder contains many profiles, clear Cache subfolder inside each
                if os.path.exists(cache_path):
                    for profile in os.listdir(cache_path):
                        profile_cache = os.path.join(cache_path, profile, 'cache2')
                        if os.path.exists(profile_cache):
                            shutil.rmtree(profile_cache, ignore_errors=True)
                    return
            else:
                return  # Add more browsers if needed

            if os.path.exists(cache_path):
                shutil.rmtree(cache_path, ignore_errors=True)
                logging.info(f"Cleared cache for {browser_name}")
        except Exception as e:
            logging.error(f"Failed to clear cache for {browser_name}: {e}")

    def _kill_network_processes(self):
        """
        Kill browser processes using network resources and clear cache before killing.
        """
        logging.debug("Checking for network-using processes")
        try:
            browsers = ['chrome.exe', 'msedge.exe', 'firefox.exe', 'opera.exe', 'brave.exe']
            for proc in psutil.process_iter(['name', 'pid']):
                proc_name = proc.info['name']
                if not proc_name:
                    continue  # Skip system or inaccessible processes

                proc_name = proc_name.lower()
                if proc_name in browsers and proc.pid not in self._killed_pids:
                    # Clear cache first
                    if self.ENABLE_CACHE_NUKE:
                        self._clear_browser_cache(proc_name)

                    try:
                        logging.info(f"Killing {proc_name} (PID: {proc.pid})")
                        proc.kill()
                        self._killed_pids.add(proc.pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        logging.warning(f"Failed to kill {proc_name} (PID: {proc.pid})")
        except Exception as e:
            logging.error(f"Error during browser process scan: {e}")

    def unlock_system(self):
        """
        Stop lockdown and restore system state.
        """
        logging.info("Unlocking system")
        self.is_locked = False
        self._stop_event.set()
        try:
            # Restore explorer.exe
            os.system("start explorer.exe")
            logging.info("Explorer.exe restored")

            # Remove firewall rule
            os.system('netsh advfirewall firewall delete rule name="LockdownBlockAll"')
            logging.info("Firewall rules removed")

            # Re-enable network adapters
            os.system('netsh interface set interface "Wi-Fi" admin=enable')
            os.system('netsh interface set interface "Ethernet" admin=enable')
            logging.info("Network adapters enabled")

            # Clear lock state
            self._clear_lock_state()

            # Check for violation decay after unlock
            self.check_violation_decay()

            # Log unlock event
            logging.debug("Logging unlock event (TODO: logger.py)")
        except Exception as e:
            logging.error(f"Error unlocking system: {e}")
        finally:
            self._killed_pids.clear()

    def reset_violation_count(self):
        """
        Reset violation count to 1 after a period of no violations (e.g., 7 days).
        """
        logging.debug("Resetting violation count")
        self.violation_count = 1
        self.last_violation_time = None
        self._save_lock_state()
        logging.info("Violation count reset to 1")

def main():
    """
    Test the lockdown module.
    """
    logging.info("Starting lockdown test")
    lockdown = Lockdown()
    lockdown.check_and_reapply_lock()  # Check for existing lock
    lockdown.lock_system()  # Test with dynamic duration
    time.sleep(2)  # Allow thread to start
    logging.info("Lockdown test completed")

if __name__ == "__main__":
    main()
    logging.info("Program exited")