import logging
import os
from keyboard_monitor import main

# Ensure the data directory exists
data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(data_dir, exist_ok=True)  # Create data directory if it doesn't exist

# Configure logging with absolute path
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [Main]: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(data_dir, "lockdown.log")),
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    try:
        logging.info("Starting main.py")
        main()  # Call keyboard_monitor.main()
        logging.info("keyboard_monitor.main() completed")
    except Exception as e:
        logging.error(f"Error in keyboard_monitor.main(): {e}", exc_info=True)
        raise