"""Root-owned NetOps system bridge.

The bridge intentionally exposes named operations instead of arbitrary shell
execution. The NetOps session can therefore manage the guest without turning
every chat input into a root command.
"""
from __future__ import annotations

import json
import os
import platform
import pwd
import shutil
import socket
import subprocess
import time
from pathlib import Path


SOCKET_PATH = Path("/run/netops/agent.sock")
STATUS_PATH = Path("/run/netops/status.json")
REMOTE_PAIRING_PATH = Path("/run/netops/remote-pairing.json")
try:
    ALLOWED_UIDS = {0, pwd.getpwnam("netops").pw_uid}
except KeyError:
    ALLOWED_UIDS = {0}


def _load() -> dict:
    state_path = Path("/var/lib/netops/axvord-state.json")
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "starting"}


def status() -> dict:
    try:
        load = os.getloadavg()[0]
    except (AttributeError, OSError):
        load = None
    result = {
        "name": "NetOps OS",
        "core": "Axvord",
        "status": "ready",
        "uid": os.getuid(),
        "hostname": platform.node(),
        "load": load,
        "disk_free": shutil.disk_usage("/").free,
        "axvord": _load(),
        "time": time.time(),
    }
    STATUS_PATH.write_text(json.dumps(result), encoding="utf-8")
    return result


def remote_pairing() -> dict:
    try:
        data = json.loads(REMOTE_PAIRING_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "beklemede", "message": "Uzaktan cihaz servisi henüz hazır değil."}
    if not isinstance(data, dict):
        return {"status": "beklemede", "message": "Uzaktan cihaz eşleştirmesi hazır değil."}
    return data


def _run_systemctl(action: str) -> dict:
    unit = "netops-axvord.service"
    command = ["/bin/systemctl", action, unit]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
    return {
        "ok": completed.returncode == 0,
        "action": action,
        "stdout": completed.stdout[-1000:],
        "stderr": completed.stderr[-1000:],
    }


def handle(request: dict) -> dict:
    action = request.get("action")
    if action == "status":
        return {"ok": True, "data": status()}
    if action == "remote_pairing":
        return {"ok": True, "data": remote_pairing()}
    if action in {"start", "stop", "restart"}:
        return _run_systemctl(action)
    if action == "reboot":
        subprocess.Popen(["/bin/systemctl", "reboot"])
        return {"ok": True, "action": action}
    if action == "poweroff":
        subprocess.Popen(["/bin/systemctl", "poweroff"])
        return {"ok": True, "action": action}
    return {"ok": False, "error": "unknown_action"}


def peer_uid(client: socket.socket) -> int:
    # Linux SO_PEERCRED prevents an unrelated local process from using the
    # bridge even if the socket path is discovered.
    credentials = client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
    return int.from_bytes(credentials[4:8], "little")


def main() -> None:
    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        SOCKET_PATH.unlink()
    except FileNotFoundError:
        pass
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(SOCKET_PATH))
        os.chmod(SOCKET_PATH, 0o660)
        try:
            netops_gid = pwd.getpwnam("netops").pw_gid
            os.chown(SOCKET_PATH.parent, 0, netops_gid)
            os.chmod(SOCKET_PATH.parent, 0o770)
            os.chown(SOCKET_PATH, 0, netops_gid)
        except KeyError:
            pass
        server.listen(8)
        status()
        while True:
            client, _ = server.accept()
            with client:
                if peer_uid(client) not in ALLOWED_UIDS:
                    client.sendall(b'{"ok":false,"error":"permission_denied"}\n')
                    continue
                data = client.recv(8192)
                try:
                    response = handle(json.loads(data.decode("utf-8")))
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    response = {"ok": False, "error": str(exc)}
                client.sendall((json.dumps(response) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
