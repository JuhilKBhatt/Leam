from pathlib import Path
from datetime import datetime
from core.utils.common import get_now

# List of patterns to filter out from logs
SPAM_FILTER = [
    "frame_index",
    "chunk",
    "loading bar",
    "Uploaded",
    "MoviePy - Writing video",
    "MoviePy - Done",
    "t:  ", # MoviePy progress line
    "|   "  # MoviePy progress line
]

def manage_log_size(log_path: Path, max_lines: int = 5000):
    """Keep only the last N lines of a log file."""
    if not log_path.exists():
        return

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) > max_lines:
            with open(log_path, "w", encoding="utf-8") as f:
                f.writelines(lines[-max_lines:])
    except Exception as e:
        print(f"Error managing log size for {log_path}: {e}")

def write_log(log_file: str | Path, message: str, level: str = "INFO"):
    """
    Append a log entry with timestamp to a log file.
    Includes filtering and size management.
    """
    message_str = str(message)

    # Filter out spam
    if any(spam in message_str for spam in SPAM_FILTER):
        return

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = get_now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {level.upper():5} | {message_str}\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)

    # Occasionally check size (e.g., 10% chance to avoid overhead on every write)
    import random
    if random.random() < 0.1:
        manage_log_size(log_path)