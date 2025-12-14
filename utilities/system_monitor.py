import psutil
import time
import json
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_FILE = Path("data/system_stats.json")
OUTPUT_FILE.parent.mkdir(exist_ok=True)

APP_START = time.time()

prev_net = psutil.net_io_counters()
prev_time = time.time()

def get_temps():
    temps = {}
    try:
        for name, entries in psutil.sensors_temperatures().items():
            temps[name] = round(entries[0].current, 1)
    except Exception:
        pass
    return temps

while True:
    time.sleep(1)

    now = time.time()
    net = psutil.net_io_counters()
    interval = now - prev_time

    stats = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": int(now - APP_START),

        "cpu": psutil.cpu_percent(),

        "memory": {
            "used": round(psutil.virtual_memory().used / 1024 / 1024, 1),
            "total": round(psutil.virtual_memory().total / 1024 / 1024, 1),
            "percent": psutil.virtual_memory().percent,
        },

        "disk": {
            "used": round(psutil.disk_usage("/").used / 1024 / 1024 / 1024, 1),
            "total": round(psutil.disk_usage("/").total / 1024 / 1024 / 1024, 1),
            "percent": psutil.disk_usage("/").percent,
        },

        "network": {
            "up": round((net.bytes_sent - prev_net.bytes_sent) / interval / 1024 / 1024, 2),
            "down": round((net.bytes_recv - prev_net.bytes_recv) / interval / 1024 / 1024, 2),
        },

        "temps": get_temps(),
    }

    OUTPUT_FILE.write_text(json.dumps(stats, indent=2))

    prev_net = net
    prev_time = now
