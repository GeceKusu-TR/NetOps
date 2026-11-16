"""Small authenticated WebSocket command service for NetOps OS.

The phone connects to this service directly after pairing. The protocol is
compatible with the Termux client, but the command surface is deliberately
allowlisted: remote clients never receive an arbitrary root shell.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import secrets
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


HOST = os.environ.get("NETOPS_REMOTE_HOST", "0.0.0.0")
PORT = int(os.environ.get("NETOPS_REMOTE_PORT", "8765"))
MAX_FRAME_SIZE = 1024 * 1024
CORE_UNIT = "netops-axvord.service"

if os.name == "nt":
    STATE_DIR = Path(os.environ.get("TEMP", ".")) / "netops-remote"
else:
    STATE_DIR = Path("/var/lib/netops")
PAIRING_PATH = Path("/run/netops/remote-pairing.json") if os.name != "nt" else STATE_DIR / "remote-pairing.json"
DEVICES_PATH = STATE_DIR / "remote-devices.json"

COMMANDS: dict[str, str] = {
    "status": "Sistem durumunu göster",
    "ram": "RAM kullanımını göster",
    "cpu": "CPU yükünü göster",
    "disk": "Disk alanını göster",
    "network": "Ağ bilgilerini göster",
    "uptime": "Çalışma süresini göster",
    "commands": "Kullanılabilir komutları göster",
    "start": "Axvord çekirdeğini başlat",
    "stop": "Axvord çekirdeğini durdur",
    "restart": "Axvord çekirdeğini yenile",
    "reboot": "NetOps OS'yi yeniden başlat",
    "poweroff": "NetOps OS'yi kapat",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return fallback


def _write_json(path: Path, value: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o640)
    except OSError:
        pass


def _memory_info() -> dict[str, int | None]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, _, raw = line.partition(":")
            parts = raw.strip().split()
            if parts and parts[0].isdigit():
                values[key] = int(parts[0]) * (1024 if len(parts) > 1 and parts[1].lower() == "kb" else 1)
    except OSError:
        pass
    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    return {
        "total": total,
        "available": available,
        "used": max(0, total - available) if total is not None and available is not None else None,
    }


def _uptime_seconds() -> float | None:
    try:
        return float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
    except (OSError, IndexError, ValueError):
        return None


def _network_info() -> dict[str, Any]:
    addresses: list[str] = []
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = str(item[4][0])
            if address not in addresses and not address.startswith("127."):
                addresses.append(address)
    except OSError:
        pass
    return {"hostname": platform.node(), "addresses": addresses}


def _status_data() -> dict[str, Any]:
    try:
        load = os.getloadavg()[0]
    except (AttributeError, OSError):
        load = None
    return {
        "name": "NetOps OS",
        "core": "Axvord",
        "status": "ready",
        "hostname": platform.node(),
        "load": load,
        "memory": _memory_info(),
        "disk_free": shutil.disk_usage("/").free,
        "uptime_seconds": _uptime_seconds(),
        "network": _network_info(),
        "time": time.time(),
    }


def _systemctl(action: str) -> dict[str, Any]:
    if action not in {"start", "stop", "restart"}:
        return {"ok": False, "error": "UNKNOWN_COMMAND"}
    try:
        completed = subprocess.run(
            ["/bin/systemctl", action, CORE_UNIT],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": completed.returncode == 0,
        "action": action,
        "display_text": "Axvord çekirdeği yenilendi." if action == "restart" and completed.returncode == 0 else "",
        "error": completed.stderr[-500:] if completed.returncode else "",
    }


def _power(action: str, args: dict[str, Any]) -> dict[str, Any]:
    if args.get("confirm") is not True:
        return {"ok": False, "error": "CONFIRMATION_REQUIRED"}
    try:
        subprocess.Popen(["/bin/systemctl", action], start_new_session=True)
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "action": action, "display_text": "İşlem başlatıldı."}


def dispatch_command(command: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute one named operation; never interpret a shell string."""
    normalized = _text(command).casefold().replace("_", "-")
    aliases = {
        "durum": "status", "bellek": "ram", "işlemci": "cpu", "islemci": "cpu",
        "depolama": "disk", "ağ": "network", "ag": "network", "çalışma-süresi": "uptime",
        "calisma-suresi": "uptime", "komutlar": "commands", "yenile": "restart",
        "yeniden-başlat": "reboot", "yeniden-baslat": "reboot", "kapat": "poweroff",
    }
    normalized = aliases.get(normalized, normalized)
    parameters = dict(args or {})
    if normalized == "status":
        return {"ok": True, "data": _status_data(), "display_text": "NetOps OS hazır."}
    if normalized == "ram":
        return {"ok": True, "data": _memory_info(), "display_text": "RAM durumu alındı."}
    if normalized == "cpu":
        data = _status_data()
        return {"ok": True, "data": {"load": data.get("load")}, "display_text": "CPU durumu alındı."}
    if normalized == "disk":
        return {"ok": True, "data": {"free": shutil.disk_usage("/").free}, "display_text": "Disk durumu alındı."}
    if normalized == "network":
        return {"ok": True, "data": _network_info(), "display_text": "Ağ durumu alındı."}
    if normalized == "uptime":
        return {"ok": True, "data": {"seconds": _uptime_seconds()}, "display_text": "Çalışma süresi alındı."}
    if normalized == "commands":
        return {
            "ok": True,
            "commands": COMMANDS,
            "policy": "Yalnızca adlandırılmış güvenli işlemler vardır; keyfi shell çalıştırılmaz.",
        }
    if normalized in {"start", "stop", "restart"}:
        return _systemctl(normalized)
    if normalized in {"reboot", "poweroff"}:
        return _power(normalized, parameters)
    return {"ok": False, "error": "UNKNOWN_COMMAND"}


def _pairing_code() -> str:
    existing = _load_json(PAIRING_PATH, {})
    code = _text(existing.get("code")) if isinstance(existing, dict) else ""
    if not (len(code) == 6 and code.isdigit()):
        code = f"{secrets.randbelow(900000) + 100000}"
    _write_json(PAIRING_PATH, {"code": code, "port": PORT, "expires_in": 0, "updated_at": time.time()})
    return code


def pairing_info() -> dict[str, Any]:
    return {"code": _pairing_code(), "port": PORT, "host": HOST}


def _authorized_devices() -> dict[str, dict[str, Any]]:
    value = _load_json(DEVICES_PATH, {})
    return value if isinstance(value, dict) else {}


def _save_device(device_id: str, record: dict[str, Any]) -> None:
    devices = _authorized_devices()
    devices[device_id] = record
    _write_json(DEVICES_PATH, devices)


def _authenticate(message: dict[str, Any]) -> dict[str, Any] | None:
    devices = _authorized_devices()
    device_id = _text(message.get("device_id"))
    token = _text(message.get("token"))
    if device_id and token and devices.get(device_id, {}).get("token") == token:
        return {"device_id": device_id, "token": token, "paired": False}
    code = _text(message.get("pairing_code"))
    if code and secrets.compare_digest(code, _pairing_code()):
        device_id = f"netops_os_{secrets.token_hex(6)}"
        token = secrets.token_urlsafe(32)
        _save_device(device_id, {"token": token, "name": _text(message.get("device_name")) or "Android cihazı", "created_at": time.time()})
        return {"device_id": device_id, "token": token, "paired": True}
    return None


def _accept_value(sock: socket.socket) -> None:
    request = bytearray()
    while b"\r\n\r\n" not in request and len(request) < 16384:
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionError("WebSocket bağlantısı kapandı.")
        request.extend(chunk)
    headers = bytes(request).decode("ascii", errors="replace").split("\r\n")
    values: dict[str, str] = {}
    for line in headers[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.casefold().strip()] = value.strip()
    key = values.get("sec-websocket-key")
    if not key or values.get("upgrade", "").casefold() != "websocket":
        raise ConnectionError("WebSocket el sıkışması reddedildi.")
    accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()).decode("ascii")
    response = "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
    sock.sendall((response + f"Sec-WebSocket-Accept: {accept}\r\n\r\n").encode("ascii"))


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("WebSocket bağlantısı kapandı.")
        data.extend(chunk)
    return bytes(data)


def _recv_frame(sock: socket.socket) -> tuple[int, bytes]:
    first, second = _recv_exact(sock, 2)
    opcode = first & 0x0F
    length = second & 0x7F
    if length == 126:
        length = int.from_bytes(_recv_exact(sock, 2), "big")
    elif length == 127:
        length = int.from_bytes(_recv_exact(sock, 8), "big")
    if length > MAX_FRAME_SIZE:
        raise ValueError("WebSocket mesajı çok büyük.")
    mask = _recv_exact(sock, 4) if second & 0x80 else b""
    payload = bytearray(_recv_exact(sock, length))
    for index, value in enumerate(payload):
        if mask:
            payload[index] = value ^ mask[index % 4]
    return opcode, bytes(payload)


def _send_frame(sock: socket.socket, opcode: int, payload: bytes = b"") -> None:
    length = len(payload)
    if length <= 125:
        header = bytes((0x80 | opcode, length))
    elif length <= 65535:
        header = bytes((0x80 | opcode, 126)) + length.to_bytes(2, "big")
    else:
        header = bytes((0x80 | opcode, 127)) + length.to_bytes(8, "big")
    sock.sendall(header + payload)


def _send_json(sock: socket.socket, value: dict[str, Any]) -> None:
    _send_frame(sock, 1, json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _assistant_command(text: str) -> tuple[str, dict[str, Any]]:
    lowered = _text(text).casefold()
    if any(word in lowered for word in ("komut", "neler yap", "yetenek")):
        return "commands", {}
    if "ram" in lowered or "bellek" in lowered:
        return "ram", {}
    if "cpu" in lowered or "işlemci" in lowered or "islemci" in lowered:
        return "cpu", {}
    if "disk" in lowered or "depolama" in lowered:
        return "disk", {}
    if "ağ" in lowered or "ag durumu" in lowered or "network" in lowered:
        return "network", {}
    if "çalışma süresi" in lowered or "uptime" in lowered:
        return "uptime", {}
    if "yeniden başlat" in lowered or "reboot" in lowered:
        return "reboot", {"confirm": "onayla" in lowered or "eminim" in lowered}
    if "kapat" in lowered or "poweroff" in lowered:
        return "poweroff", {"confirm": "onayla" in lowered or "eminim" in lowered}
    if "yenile" in lowered or "çekirdeği başlat" in lowered or "cekirdegi baslat" in lowered:
        return "restart", {}
    return "status", {}


def _handle_client(client: socket.socket) -> None:
    authenticated: dict[str, Any] | None = None
    client.settimeout(60)
    try:
        _accept_value(client)
        while True:
            opcode, payload = _recv_frame(client)
            if opcode == 8:
                return
            if opcode == 9:
                _send_frame(client, 10, payload)
                continue
            if opcode != 1:
                continue
            message = json.loads(payload.decode("utf-8"))
            if not isinstance(message, dict):
                _send_json(client, {"type": "error", "error": "INVALID_JSON"})
                continue
            kind = _text(message.get("type")).casefold()
            if kind == "hello":
                authenticated = _authenticate(message)
                if not authenticated:
                    _send_json(client, {"type": "hello_result", "ok": False, "error": "PAIRING_REQUIRED"})
                    return
                _send_json(client, {"type": "hello_result", "ok": True, **authenticated, "heartbeat_interval": 10, "device": {"name": "NetOps OS", "core": "Axvord"}})
                continue
            if kind == "heartbeat":
                if not authenticated:
                    _send_json(client, {"type": "error", "error": "PAIRING_REQUIRED"})
                    continue
                _send_json(client, {"type": "heartbeat_ack", "device_id": authenticated["device_id"], "timestamp": time.time()})
                continue
            if not authenticated:
                _send_json(client, {"type": "error", "error": "PAIRING_REQUIRED"})
                continue
            if kind == "assistant_request":
                request_id = _text(message.get("id")) or f"remote_{secrets.token_hex(8)}"
                command, args = _assistant_command(_text(message.get("text")))
                result = dispatch_command(command, args)
                _send_json(client, {"type": "assistant_response", "id": request_id, **result})
                continue
            if kind == "command":
                command_id = _text(message.get("id")) or f"command_{secrets.token_hex(8)}"
                values = message.get("args") if isinstance(message.get("args"), dict) else {}
                result = dispatch_command(_text(message.get("command")), values)
                _send_json(client, {"type": "command_result", "id": command_id, **result})
                continue
            _send_json(client, {"type": "error", "error": "UNSUPPORTED_MESSAGE"})
    except (ConnectionError, OSError, ValueError, json.JSONDecodeError, socket.timeout):
        return
    finally:
        try:
            client.close()
        except OSError:
            pass


def serve_forever() -> None:
    _pairing_code()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(16)
        while True:
            client, _ = server.accept()
            threading.Thread(target=_handle_client, args=(client,), daemon=True).start()


if __name__ == "__main__":
    serve_forever()
