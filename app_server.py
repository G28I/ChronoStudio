"""
app_server.py — Application Desktop Host & API Server
Serves the HTML5/WebGL2 desktop UI, binds to the MediaEngineWorker,
and provides HTTP endpoints for project persistence, frame scrubbing, and export.
"""

import os
import sys
import json
from http.server import SimpleHTTPRequestHandler, HTTPServer
import urllib.parse

from core.time_model import RationalTime, TimeRange, ClipItem
from core.timeline_model import TimelineModel
from core.media_importer import MediaImporter
from core.media_compositor import MediaCompositor
from core.export_pipeline import ExportPipeline
from core.transactional_journal import ProjectModel, TransactionalPersistenceEngine


# Global App State
importer = MediaImporter()
timeline = TimelineModel(timebase_rate=60)
compositor = MediaCompositor(importer)
exporter = ExportPipeline(importer, compositor)
persistence = TransactionalPersistenceEngine("project_phase1.cpj")

# Populate initial representative 5-clip timeline across 2 video and 2 audio tracks
test_media_path = os.path.abspath("spikes/test_1080p60.mp4")
a1 = importer.import_asset("asset_01", test_media_path)
a2 = importer.import_asset("asset_02", test_media_path)
a_offline = importer.import_asset("asset_offline", "nonexistent_clip.mov")

# 5 clips:
# V1: Clip 1 [0 -> 180), Clip 2 [180 -> 300)
c_v1_1 = ClipItem("c_v1_1", "asset_01", TimeRange(RationalTime(0, 60), RationalTime(180, 60)), RationalTime(0, 60))
c_v1_2 = ClipItem("c_v1_2", "asset_01", TimeRange(RationalTime(180, 60), RationalTime(120, 60)), RationalTime(180, 60))
# V2: Clip 3 (Overlay) [60 -> 240)
c_v2_1 = ClipItem("c_v2_1", "asset_02", TimeRange(RationalTime(60, 60), RationalTime(180, 60)), RationalTime(0, 60))
# A1: Clip 4 [0 -> 300)
c_a1_1 = ClipItem("c_a1_1", "asset_01", TimeRange(RationalTime(0, 60), RationalTime(300, 60)), RationalTime(0, 60))
# A2: Clip 5 [60 -> 240)
c_a2_1 = ClipItem("c_a2_1", "asset_02", TimeRange(RationalTime(60, 60), RationalTime(180, 60)), RationalTime(0, 60))

timeline.add_clip("V1", c_v1_1)
timeline.add_clip("V1", c_v1_2)
timeline.add_clip("V2", c_v2_1)
timeline.add_clip("A1", c_a1_1)
timeline.add_clip("A2", c_a2_1)


class EditorRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.abspath("ui"), **kwargs)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status_data = {
                "sequence_duration_frames": timeline.duration.rescale(60).value,
                "fps": 60,
                "video_tracks": {k: len(v.clips) for k, v in timeline.video_tracks.items()},
                "audio_tracks": {k: len(v.clips) for k, v in timeline.audio_tracks.items()},
                "assets_imported": len(importer.asset_registry)
            }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
        else:
            super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/export":
            out_file = os.path.abspath("exports/phase1_export.mp4")
            res = exporter.export_timeline(timeline, out_file)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
        elif url.path == "/api/save":
            model = ProjectModel("phase1_project")
            model.last_applied_tx_id = 10
            persistence.write_atomic_snapshot(model)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "saved"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_app_server(port: int = 8080):
    server = HTTPServer(("127.0.0.1", port), EditorRequestHandler)
    print(f"ChronoStudio Editor Desktop Server running on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    port = 8080
    if "--port" in sys.argv:
        p_idx = sys.argv.index("--port") + 1
        if p_idx < len(sys.argv):
            port = int(sys.argv[p_idx])
    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_app_server(port)
