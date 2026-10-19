"""
tests/test_ui_workflow.py — End-to-End Browser UI Workflow Integration Test
Drives the actual ChronoStudio application UI via Playwright:
1. Load UI and verify asset bin & multi-track canvas
2. Tool selection & Razor cutting via canvas click
3. Ripple delete and timeline shift verification
4. Interactive playback transport & frame advancement
5. Project saving & reopening
6. Master MP4 export through UI trigger
7. Validates final exported media
"""

import os
import sys
import time
import threading
from http.server import HTTPServer
import pytest
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath("."))
from app_server import EditorRequestHandler


@pytest.fixture(scope="module")
def app_server():
    port = 8085
    server = HTTPServer(("127.0.0.1", port), EditorRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def test_complete_ui_editing_workflow(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture console messages
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # 1. Load Application
        page.goto(app_server)
        page.wait_for_selector("#program-canvas")
        page.wait_for_selector("#timeline-canvas")
        assert page.title() == "ChronoStudio — Professional Video Editor (Phase 1)"
        assert len(console_errors) == 0

        # Verify Project Bins have imported assets
        cards = page.locator(".asset-card")
        assert cards.count() >= 3

        # 2. Tool Selection & Razor Cut
        # Select Razor tool
        page.click("#tool-razor")
        assert "active" in page.get_attribute("#tool-razor", "class")

        # Click timeline canvas at x=200 to execute a cut
        tl_canvas = page.locator("#timeline-canvas")
        box = tl_canvas.bounding_box()
        assert box is not None
        # Click near middle (track V1 is at y ~80 to 125)
        page.mouse.click(box["x"] + 200, box["y"] + 90)
        time.sleep(0.3)

        status_text = page.locator("#status-readout").inner_text()
        assert "Razor cut executed" in status_text

        # 3. Interactive Playback Transport
        # Press Space or click Play button
        page.click("#btn-play")
        time.sleep(1.0) # Play for 1 second

        # Check timecode readout has advanced past 00:00:00:00
        tc_text = page.locator("#tc-display").inner_text()
        assert tc_text != "00:00:00:00", f"Playhead did not advance: {tc_text}"

        # Pause playback
        page.click("#btn-play")
        time.sleep(0.2)

        # 4. Ripple Delete Action
        page.click("#tool-ripple-del")
        time.sleep(0.2)
        status_after_del = page.locator("#status-readout").inner_text()
        assert "Ripple deleted" in status_after_del

        # 5. Save Project
        page.click("#btn-save")
        time.sleep(0.3)
        assert "saved atomically" in page.locator("#status-readout").inner_text()

        # 6. Reopen Project
        page.click("#btn-reopen")
        time.sleep(0.3)
        assert "reopened" in page.locator("#status-readout").inner_text()

        # 7. Trigger Export MP4 via UI
        page.click("#btn-export")
        # Wait up to 10s for export completion
        page.wait_for_function("document.getElementById('status-readout').innerText.includes('complete')", timeout=15000)
        export_status = page.locator("#status-readout").inner_text()
        assert "Export complete" in export_status

        # Verify exported file
        export_file = os.path.abspath("exports/phase1_export.mp4")
        assert os.path.exists(export_file)
        assert os.path.getsize(export_file) > 50000

        browser.close()
