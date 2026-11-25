"""Minimal RFC 6455 WebSocket client (stdlib only) for ComfyUI's /ws progress stream.
Supports text frames, ping/pong, close, fragmented messages; binary frames (previews) are skipped."""
from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import struct
from urllib.parse import urlparse


class WebSocketError(OSError):
    pass


class WebSocket:
    def __init__(self, url: str, timeout: float = 10.0, headers: dict | None = None):
        u = urlparse(url)
        if u.scheme not in ("ws", "wss"):
            raise WebSocketError("URL must be ws:// or wss://")
        port = u.port or (443 if u.scheme == "wss" else 80)
        sock = socket.create_connection((u.hostname, port), timeout=timeout)
        if u.scheme == "wss":
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=u.hostname)
        self.sock = sock
        self._buf = b""
        key = base64.b64encode(os.urandom(16)).decode()
        path = (u.path or "/") + (("?" + u.query) if u.query else "")
        lines = [f"GET {path} HTTP/1.1", f"Host: {u.hostname}:{port}", "Upgrade: websocket", "Connection: Upgrade",
                 f"Sec-WebSocket-Key: {key}", "Sec-WebSocket-Version: 13"]
        for k, v in (headers or {}).items():
            lines.append(f"{k}: {v}")
        sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        resp = self._read_until(b"\r\n\r\n")
        status = resp.split(b"\r\n", 1)[0]
        if b" 101 " not in status:
            raise WebSocketError(f"WebSocket upgrade failed: {status.decode(errors='replace')}")
        import hashlib
        expect = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest())
        if expect not in resp:
            raise WebSocketError("Bad Sec-WebSocket-Accept")

    def settimeout(self, t):
        self.sock.settimeout(t)

    def _read_until(self, marker: bytes) -> bytes:
        while marker not in self._buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise WebSocketError("Connection closed during handshake")
            self._buf += chunk
        head, self._buf = self._buf.split(marker, 1)
        return head + marker

    def _recv_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = self.sock.recv(max(4096, n - len(self._buf)))
            if not chunk:
                raise WebSocketError("Connection closed")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _send_frame(self, opcode: int, payload: bytes = b""):
        mask = os.urandom(4)
        n = len(payload)
        if n < 126:
            hdr = struct.pack("!BB", 0x80 | opcode, 0x80 | n)
        elif n < 65536:
            hdr = struct.pack("!BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            hdr = struct.pack("!BBQ", 0x80 | opcode, 0x80 | 127, n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(hdr + mask + masked)

    def recv(self):
        """Return next text message (str), or None on close. Raises socket.timeout on timeout."""
        parts, op0 = [], None
        while True:
            b1, b2 = self._recv_exact(2)
            fin, op = b1 & 0x80, b1 & 0x0F
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack("!H", self._recv_exact(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if b2 & 0x80 else None
            data = self._recv_exact(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if op == 0x8:
                try:
                    self._send_frame(0x8, data[:2])
                except OSError:
                    pass
                return None
            if op == 0x9:
                self._send_frame(0xA, data)
                continue
            if op == 0xA:
                continue
            if op in (0x1, 0x2):
                op0, parts = op, [data]
            elif op == 0x0:
                parts.append(data)
            if fin:
                if op0 == 0x1:
                    return b"".join(parts).decode("utf-8", errors="replace")
                parts, op0 = [], None  # binary preview frame: ignore

    def recv_json(self):
        m = self.recv()
        return None if m is None else json.loads(m)

    def close(self):
        try:
            self._send_frame(0x8, struct.pack("!H", 1000))
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass
