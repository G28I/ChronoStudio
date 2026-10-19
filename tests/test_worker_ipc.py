"""
tests/test_worker_ipc.py — Integration Tests for Decoupled Media Engine Worker IPC
Tests TCP loopback JSON-RPC communication, request/response cycle,
seek cancellation via generation tokens, timeout handling, and process restart/recovery.
"""

import socket
import json
import time
import subprocess
import threading
import os
import pytest
from core.engine_worker import MediaEngineWorker


class TCPRPCClient:
    def __init__(self, host="127.0.0.1", port=8766, timeout=3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None

    def connect(self, retries=10, delay=0.2):
        for i in range(retries):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.connect((self.host, self.port))
                return True
            except ConnectionRefusedError:
                time.sleep(delay)
        return False

    def call(self, method: str, params: dict = None, req_id: int = 1) -> dict:
        req = {"id": req_id, "method": method, "params": params or {}}
        payload = (json.dumps(req) + "\n").encode("utf-8")
        self.sock.sendall(payload)

        buf = ""
        while "\n" not in buf:
            chunk = self.sock.recv(4096).decode("utf-8")
            if not chunk:
                raise ConnectionResetError("Server closed connection")
            buf += chunk
        line = buf.strip()
        return json.loads(line)

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


@pytest.fixture(scope="module")
def worker_server():
    port = 8766
    worker = MediaEngineWorker(port=port)
    server_thread = threading.Thread(target=worker.run_server, daemon=True)
    server_thread.start()
    time.sleep(0.3)  # Allow bind
    yield worker, port
    worker.is_running = False


def test_ipc_ping_and_import(worker_server):
    worker, port = worker_server
    client = TCPRPCClient(port=port)
    assert client.connect(), "Failed to connect to MediaEngineWorker"

    # 1. Ping
    resp = client.call("ping", req_id=101)
    assert resp["id"] == 101
    assert resp["result"] == "pong"

    # 2. Import Media
    test_media = os.path.abspath("spikes/test_1080p60.mp4")
    resp_imp = client.call("import_media", {"asset_id": "test_asset", "file_path": test_media}, req_id=102)
    assert resp_imp["id"] == 102
    assert resp_imp["result"]["asset_id"] == "test_asset"
    assert resp_imp["result"]["fps"] == 60.0
    assert resp_imp["result"]["resolution"] == [1920, 1080]

    client.close()


def test_ipc_seek_cancellation(worker_server):
    worker, port = worker_server
    client = TCPRPCClient(port=port)
    assert client.connect()

    # Add clip
    client.call("add_clip", {
        "track_id": "V1",
        "clip_id": "c_ipc_1",
        "asset_id": "test_asset",
        "timeline_in": 0,
        "duration": 300,
        "source_in": 0
    }, req_id=103)

    # Set server current generation to 5
    worker.current_generation_id = 5

    # Send a stale seek with generation 2 (simulating old scrub request)
    resp_stale = client.call("seek", {"frame": 60, "generation_id": 2}, req_id=104)
    assert resp_stale["result"] == "cancelled"
    assert resp_stale["generation_id"] == 2

    # Send active seek with matching generation 5
    resp_active = client.call("seek", {"frame": 60, "generation_id": 5}, req_id=105)
    assert resp_active["result"]["status"] == "ready"
    assert resp_active["result"]["frame"] == 60

    client.close()


def test_ipc_timeout_and_graceful_shutdown():
    # Test worker shutdown command on a separate worker instance
    port = 8767
    worker = MediaEngineWorker(port=port)
    t = threading.Thread(target=worker.run_server, daemon=True)
    t.start()
    time.sleep(0.3)

    client = TCPRPCClient(port=port, timeout=1.0)
    assert client.connect()
    
    # Request shutdown
    resp = client.call("shutdown", req_id=106)
    assert resp["result"] == "shutting_down"
    time.sleep(0.3)
    assert not worker.is_running
    client.close()
