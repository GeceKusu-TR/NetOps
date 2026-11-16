"""Small client for the root-owned NetOps system bridge."""
from __future__ import annotations

import json
import socket
import sys


SOCKET_PATH = "/run/netops/agent.sock"


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    request = json.dumps({"action": action}).encode("utf-8")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(SOCKET_PATH)
        client.sendall(request)
        response = client.recv(8192)
    print(json.dumps(json.loads(response.decode("utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
