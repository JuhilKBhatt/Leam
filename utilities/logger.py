from pathlib import Path
from datetime import datetime


def write_log(log_file: str | Path, message: str, level: str = "INFO"):
    """
    Append a log entry with timestamp to a log file.

    Args:
        log_file (str | Path): Path to the log file
        message (str): Log message
        level (str): INFO, ERROR, WARN, DEBUG
    """

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {level.upper():5} | {message}\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)