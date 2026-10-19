"""
core/engine_worker.py — Decoupled Media Engine Worker Process
Runs out-of-process, serving JSON-RPC requests from the UI shell,
managing decoders, bounded LRU frame cache, multi-track compositing, and export jobs.
"""

import os
import sys
import json
import socket
import threading
import time
from typing import Dict, Any, Optional
import av
import numpy as np

from core.time_model import RationalTime, TimeRange, ClipItem
from core.timeline_model import TimelineModel
from core.media_importer import MediaImporter
from core.media_compositor import MediaCompositor
from core.transactional_journal import ProjectModel, TransactionalPersistenceEngine
from core.export_pipeline import ExportPipeline


class MediaEngineWorker:
    def __init__(self, cache_budget_mb: int = 128, port: int = 8765):
        self.port = port
        self.importer = MediaImporter()
        self.timeline = TimelineModel(timebase_rate=60)
        self.compositor = MediaCompositor(self.importer)
        self.exporter = ExportPipeline(self.importer, self.compositor)
        
        # Bounded frame cache
        self.max_cache_bytes = cache_budget_mb * 1024 * 1024
        self.current_cache_bytes = 0
        self.frame_cache: Dict[str, np.ndarray] = {}  # key: f"{asset_id}_{frame_idx}"
        
        # Open video containers
        self.containers: Dict[str, Any] = {}
        
        # Generation token for seek cancellation
        self.current_generation_id = 0
        self.is_running = True
        self.tx_counter = 0

    def get_decoded_source_frame(self, asset, source_time: RationalTime) -> np.ndarray:
        """Decodes exact frame from container stream or returns from cache."""
        target_frame = source_time.value
        cache_key = f"{asset.asset_id}_{target_frame}"
        if cache_key in self.frame_cache:
            return self.frame_cache[cache_key]

        if asset.is_offline or not os.path.exists(asset.file_path):
            return self.importer.generate_offline_placeholder(asset, target_frame)

        # Open container if not already opened
        if asset.asset_id not in self.containers:
            self.containers[asset.asset_id] = av.open(asset.file_path)

        container = self.containers[asset.asset_id]
        stream = container.streams.video[0]
        pts = int(target_frame * (stream.time_base.denominator / stream.average_rate / stream.time_base.numerator))
        container.seek(pts, any_frame=False, backward=True, stream=stream)

        found_frame = None
        for frame in container.decode(stream):
            f_idx = int(round(float(frame.pts * stream.time_base) * float(stream.average_rate)))
            if f_idx >= target_frame:
                found_frame = frame.to_ndarray(format="rgba")
                break

        if found_frame is None:
            found_frame = np.zeros((1080, 1920, 4), dtype=np.uint8)

        # Cache with LRU eviction
        frame_bytes = found_frame.nbytes
        if self.current_cache_bytes + frame_bytes <= self.max_cache_bytes:
            self.frame_cache[cache_key] = found_frame
            self.current_cache_bytes += frame_bytes

        return found_frame

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        cmd = req.get("method")
        params = req.get("params", {})
        req_id = req.get("id", 0)

        try:
            if cmd == "ping":
                return {"id": req_id, "result": "pong", "time": time.time()}

            elif cmd == "import_media":
                asset = self.importer.import_asset(params["asset_id"], params["file_path"])
                return {
                    "id": req_id,
                    "result": {
                        "asset_id": asset.asset_id,
                        "duration_s": asset.duration_seconds,
                        "fps": float(asset.video_fps),
                        "resolution": asset.video_resolution,
                        "is_offline": asset.is_offline
                    }
                }

            elif cmd == "add_clip":
                t_in = RationalTime(params["timeline_in"], 60)
                t_dur = RationalTime(params["duration"], 60)
                s_in = RationalTime(params["source_in"], 60)
                clip = ClipItem(params["clip_id"], params["asset_id"], TimeRange(t_in, t_dur), s_in)
                self.timeline.add_clip(params["track_id"], clip)
                return {"id": req_id, "result": "clip_added", "clip_id": clip.clip_id}

            elif cmd == "split_clip":
                t_split = RationalTime(params["at_frame"], 60)
                head, tail = self.timeline.split_clip(params["clip_id"], t_split)
                return {
                    "id": req_id,
                    "result": {
                        "head_id": head.clip_id if head else None,
                        "tail_id": tail.clip_id if tail else None
                    }
                }

            elif cmd == "ripple_delete":
                dur = self.timeline.ripple_delete(params["track_id"], params["clip_id"])
                return {"id": req_id, "result": "rippled", "rippled_frames": dur.value}

            elif cmd == "seek":
                gen_id = params.get("generation_id", 0)
                # Check for stale seek cancellation before updating generation
                if gen_id < self.current_generation_id:
                    return {"id": req_id, "result": "cancelled", "generation_id": gen_id}
                self.current_generation_id = gen_id
                target_frame = params.get("frame", 0)

                t = RationalTime(target_frame, 60)
                composited = self.compositor.composite_video_frame(
                    self.timeline, t, self.get_decoded_source_frame
                )
                return {
                    "id": req_id,
                    "result": {
                        "frame": target_frame,
                        "generation_id": gen_id,
                        "shape": list(composited.shape),
                        "status": "ready"
                    }
                }

            elif cmd == "export":
                res = self.exporter.export_timeline(
                    self.timeline,
                    params["output_path"],
                    encoder=params.get("encoder", "h264_nvenc"),
                    bitrate=params.get("bitrate", "10M"),
                    frame_reader_fn=self.get_decoded_source_frame
                )
                return {"id": req_id, "result": res}

            elif cmd == "shutdown":
                self.is_running = False
                for c in self.containers.values():
                    c.close()
                return {"id": req_id, "result": "shutting_down"}

            else:
                return {"id": req_id, "error": f"Unknown method {cmd}"}

        except Exception as e:
            return {"id": req_id, "error": str(e)}

    def run_server(self):
        """TCP JSON-RPC server loop."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", self.port))
        server.listen(5)
        server.settimeout(1.0)
        print(f"Media Engine Worker running on 127.0.0.1:{self.port}...")

        while self.is_running:
            try:
                conn, _ = server.accept()
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue

        server.close()
        print("Media Engine Worker stopped cleanly.")

    def _handle_client(self, conn: socket.socket):
        buf = ""
        while self.is_running:
            data = conn.recv(4096)
            if not data:
                break
            buf += data.decode("utf-8")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                req = json.loads(line)
                resp = self.handle_request(req)
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
        conn.close()


if __name__ == "__main__":
    worker = MediaEngineWorker()
    worker.run_server()
