import os
from datetime import datetime
import logzero


def setup_log():
    # Create a dynamic folder and file name based on the date
    log_folder = datetime.now().strftime("%Y-%m")
    day = datetime.now().strftime("%d")
    log_file = f"logs/{log_folder}/{day}_app.log"

    # Create the log directory if it does not exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs(f"logs/{log_folder}", exist_ok=True)

    # Set up log file to capture all log levels
    logzero.logfile(log_file, loglevel=logzero.logging.INFO, mode="a")
