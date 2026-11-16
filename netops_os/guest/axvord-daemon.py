"""Minimal Axvord service marker for the first QEMU image."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


STATE = Path("/var/lib/netops/axvord-state.json")


def main() -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    while True:
        STATE.write_text(json.dumps({"name": "Axvord", "status": "ready", "pid": os.getpid(), "time": time.time()}), encoding="utf-8")
        time.sleep(10)


if __name__ == "__main__":
    main()
