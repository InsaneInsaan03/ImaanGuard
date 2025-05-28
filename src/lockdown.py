import os
import time
import json
import psutil
import threading
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import shutil
import os

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
        self.ENABLE_CACHE_NUKE = False  # Set to True in production
        self.is_bypass = False
        self._lock_thread = None
        self._stop_event = threading.Event()
        self._killed_pids = set()  # Track killed PIDs to avoid redundant kills
        logging.info("Lockdown manager initialized")

    def lock_system(self, duration: int, is_bypass: bool = False):
        """
        Enforce lockdown in a background thread.
        
        Args:
            duration: Lock duration in seconds (e.g., 7200 for 2h, 172800 for 2 days).
            is_bypass: True if triggered by bypass attempt (2-day lock).
        """
        logging.info(f"Locking system for {duration} seconds (Bypass: {is_bypass})")
        self.is_locked = True
        self.lock_duration = duration
        self._killed_pids = set()
        self.lock_end_time = time.time() + duration
        self.is_bypass = is_bypass
        self._stop_event.clear()
        self._killed_pids.clear()

        # Save lock state
        self._save_lock_state()

        # Log event (placeholder for logger.py)
        logging.debug("Logging lockdown event (TODO: logger.py)")

        # Start lockdown in background thread
        self._lock_thread = threading.Thread(target=self._lock_loop)
        self._lock_thread.start()

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
                executor.submit(self._kill_explorer)
                executor.submit(self._block_tools)
                executor.submit(self._kill_network_processes)                
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
                remaining_duration = state['lock_end_time'] - time.time()
                logging.info(f"Reapplying lock for {remaining_duration} seconds")
                self.lock_system(max(0, int(remaining_duration)), is_bypass=state.get('is_bypass', False))
            else:
                logging.info("No active lock or lock expired")
                self._clear_lock_state()
        except FileNotFoundError:
            logging.debug("No lock file found, no lock to reapply")
        except Exception as e:
            logging.error(f"Error checking lock state: {e}")

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
                'is_bypass': self.is_bypass
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

            # Log unlock event
            logging.debug("Logging unlock event (TODO: logger.py)")
        except Exception as e:
            logging.error(f"Error unlocking system: {e}")
        finally:
            self._killed_pids.clear()

def main():
    """
    Test the lockdown module.
    """
    logging.info("Starting lockdown test")
    lockdown = Lockdown()
    lockdown.check_and_reapply_lock()  # Check for existing lock
    lockdown.lock_system(duration=30)  # Test with 30-second lock
    time.sleep(2)  # Allow thread to start
    logging.info("Lockdown test completed")

if __name__ == "__main__":
    main()
    logging.info("Program exited")

