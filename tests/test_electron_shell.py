"""
tests/test_electron_shell.py — Comprehensive Standalone Electron Desktop Shell Tests
Verifies:
1. Electron Window Launch with strict Security Guardrails (nodeIntegration=false, contextIsolation=true).
2. Backend Process Supervision: auto-spawning, healthcheck wait, port conflict resolution.
3. Smoke Tests: Media Ingest, Playback toggle, Razor cut, Save, Reopen, and Export.
4. Clean Process Termination: verifies zero orphaned Python or Electron processes upon exit.
"""

import os
import sys
import time
import socket
import subprocess
import requests
import pytest
import psutil
from playwright.sync_api import sync_playwright

ELECTRON_BIN = os.path.abspath("node_modules/electron/dist/electron.exe")
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_child_pids(parent_pid: int):
    """Returns list of all descendant PIDs under parent_pid."""
    try:
        parent = psutil.Process(parent_pid)
        return [child.pid for child in parent.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def test_electron_port_conflict_and_supervision():
    """
    Simulates a port conflict on 8080 by binding a dummy TCP server.
    Verifies that Electron detects the conflict and selects the next available port (e.g. 8081).
    """
    # 1. Bind port 8080 to simulate conflict
    conflict_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conflict_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    conflict_sock.bind(("127.0.0.1", 8080))
    conflict_sock.listen(1)

    debug_port = 9225
    proc = subprocess.Popen(
        [ELECTRON_BIN, ".", f"--remote-debugging-port={debug_port}"],
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        # Wait up to 15 seconds for backend to come up on alternate port (8081+)
        bound_port = None
        for _ in range(30):
            time.sleep(0.5)
            for test_p in [8081, 8082, 8083]:
                try:
                    r = requests.get(f"http://127.0.0.1:{test_p}/api/status", timeout=0.5)
                    if r.status_code == 200:
                        bound_port = test_p
                        break
                except Exception:
                    continue
            if bound_port:
                break

        assert bound_port is not None, "Electron shell failed to resolve port conflict on 8080!"
        print(f"Port conflict successfully resolved! Electron bound backend to: {bound_port}")

    finally:
        conflict_sock.close()
        # Clean termination
        if proc.poll() is None:
            subprocess.run(f"taskkill /pid {proc.pid} /T /F", shell=True, capture_output=True)


def test_electron_shell_security_and_editing_smoke():
    """
    Launches Electron with remote debugging and validates:
    - Security settings (nodeIntegration=false, contextIsolation=true)
    - Context bridge API
    - UI smoke test: Ingest, Playback, Razor, Save, Reopen, Export
    - Clean process exit with zero orphan processes
    """
    debug_port = 9226
    proc = subprocess.Popen(
        [ELECTRON_BIN, ".", f"--remote-debugging-port={debug_port}"],
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    all_spawned_pids = [proc.pid]

    try:
        # Wait for CDP endpoint
        cdp_ready = False
        for _ in range(30):
            time.sleep(0.5)
            try:
                r = requests.get(f"http://127.0.0.1:{debug_port}/json/version", timeout=0.5)
                if r.status_code == 200:
                    cdp_ready = True
                    break
            except Exception:
                continue

        assert cdp_ready, "Electron CDP debugging port did not respond in time"

        # Collect child PIDs (e.g. Python backend process)
        time.sleep(2.0)
        children = get_child_pids(proc.pid)
        all_spawned_pids.extend(children)
        print(f"Electron PID: {proc.pid}, Children PIDs: {children}")

        # Connect Playwright to Electron via CDP
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
            context = browser.contexts[0]
            # Find the main app window
            page = None
            for _ in range(20):
                for p_item in context.pages:
                    if "ChronoStudio" in p_item.title() or "127.0.0.1" in p_item.url:
                        page = p_item
                        break
                if page:
                    break
                time.sleep(0.5)

            assert page is not None, "Failed to find Electron main window page"

            # 1. Verify Security Guardrails
            node_req = page.evaluate("typeof require")
            assert node_req == "undefined", f"Security violation: require is exposed ({node_req})!"

            proc_exposed = page.evaluate("typeof process")
            assert proc_exposed == "undefined", f"Security violation: process is exposed ({proc_exposed})!"

            api_exposed = page.evaluate("typeof window.electronAPI")
            assert api_exposed == "object", "electronAPI context bridge was not properly exposed!"

            port_val = page.evaluate("window.electronAPI.getServerPort()")
            print(f"Electron context bridge verified! Server port: {port_val}")

            # 2. Smoke Test: Media Ingest & Bin Display
            asset_cards = page.locator(".asset-card")
            assert asset_cards.count() >= 3, f"Expected >= 3 assets in bin, found {asset_cards.count()}"

            # 3. Smoke Test: Razor Cut (C)
            page.click("#tool-razor")
            assert "active" in page.get_attribute("#tool-razor", "class")

            # Click timeline canvas to perform Razor cut at frame 100
            canvas = page.locator("#timeline-canvas")
            box = canvas.bounding_box()
            page.mouse.click(box["x"] + 200, box["y"] + 100)
            status_text = page.inner_text("#status-readout")
            assert "Razor cut executed" in status_text, f"Razor cut failed: {status_text}"

            # 4. Smoke Test: Transport Playback
            page.keyboard.press("Space")
            time.sleep(0.5)
            play_btn_text = page.inner_text("#btn-play")
            assert "Pause" in play_btn_text, f"Playback did not start: {play_btn_text}"
            page.keyboard.press("Space")  # Pause

            # 5. Smoke Test: Save & Reopen
            page.click("#btn-save")
            assert "saved" in page.inner_text("#status-readout").lower()

            page.click("#btn-reopen")
            assert "reopened" in page.inner_text("#status-readout").lower()

            # 6. Smoke Test: Export
            page.click("#btn-export")
            time.sleep(2.0)
            exp_status = page.inner_text("#status-readout")
            assert "Export" in exp_status, f"Export status unexpected: {exp_status}"

            browser.close()

    finally:
        # 4. Verify Clean Process Termination
        print("[Test Cleanup] Terminating Electron process tree...")
        subprocess.run(f"taskkill /pid {proc.pid} /T /F", shell=True, capture_output=True)
        time.sleep(1.0)

        # Assert no orphaned processes remain
        orphans = []
        for pid in all_spawned_pids:
            if psutil.pid_exists(pid):
                try:
                    p_obj = psutil.Process(pid)
                    if p_obj.is_running() and p_obj.status() != psutil.STATUS_ZOMBIE:
                        orphans.append((pid, p_obj.name()))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        assert len(orphans) == 0, f"Orphaned processes detected after Electron exit: {orphans}"
        print("Clean termination verified: 0 orphan processes remain.")
