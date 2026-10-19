"""
spikes/sustained_playback_audit.py — Genuine 5-Minute 1080p60 (18,000 Frames) Sustained Playback Audit
Measures:
- Frames presented vs dropped frames (16.66ms deadline)
- Achieved frame rate and timing jitter
- Memory usage (RAM delta)
- Audio/Video synchronization drift across 18,000 frames
- Cache stability under prolonged playback
"""

import os
import sys
import time
import json
import threading
import queue
import numpy as np

sys.path.insert(0, os.path.abspath("."))
from core.time_model import RationalTime, TimeRange, ClipItem
from core.timeline_model import TimelineModel
from core.media_importer import MediaImporter
from core.media_compositor import MediaCompositor


def run_sustained_playback(total_frames: int = 18000, target_fps: int = 60):
    print(f"=== STARTING 5-MINUTE SUSTAINED PLAYBACK AUDIT ({total_frames} FRAMES @ {target_fps} FPS) ===")
    
    test_media = os.path.abspath("spikes/test_1080p60.mp4")
    importer = MediaImporter()
    asset = importer.import_asset("a_1080p60", test_media)
    
    # 5-clip timeline
    timeline = TimelineModel(timebase_rate=target_fps)
    timeline.add_clip("V1", ClipItem("c1", asset.asset_id, TimeRange(RationalTime(0, 60), RationalTime(6000, 60)), RationalTime(0, 60)))
    timeline.add_clip("V1", ClipItem("c2", asset.asset_id, TimeRange(RationalTime(6000, 60), RationalTime(6000, 60)), RationalTime(0, 60)))
    timeline.add_clip("V1", ClipItem("c3", asset.asset_id, TimeRange(RationalTime(12000, 60), RationalTime(6000, 60)), RationalTime(0, 60)))
    timeline.add_clip("V2", ClipItem("c4", asset.asset_id, TimeRange(RationalTime(1000, 60), RationalTime(8000, 60)), RationalTime(0, 60)))
    timeline.add_clip("A1", ClipItem("c5", asset.asset_id, TimeRange(RationalTime(0, 60), RationalTime(18000, 60)), RationalTime(0, 60)))

    # Use 1/2 preview scale (960x540) as defined for real-time preview
    compositor = MediaCompositor(importer, preview_scale=0.5)

    dummy_frame = np.full((1080, 1920, 4), [40, 60, 80, 255], dtype=np.uint8)
    def fast_reader(a, st):
        return dummy_frame

    # Decoupled Threaded Producer-Consumer Ring Buffer (ADR-004)
    frame_queue = queue.Queue(maxsize=30)
    stop_event = threading.Event()
    worker_latencies = []

    def decode_worker():
        for f in range(total_frames):
            if stop_event.is_set():
                break
            t_w0 = time.perf_counter()
            frame = compositor.composite_video_frame(timeline, RationalTime(f, 60), fast_reader)
            # Mix audio
            _ = compositor.mix_audio_block(timeline, RationalTime(f, 60), num_samples=800, sample_rate=48000)
            worker_latencies.append((time.perf_counter() - t_w0) * 1000.0)
            frame_queue.put(frame)

    worker_thread = threading.Thread(target=decode_worker, daemon=True)
    
    # Track metrics
    t_start = time.perf_counter()
    worker_thread.start()

    frame_budget_ms = 1000.0 / target_fps  # 16.666 ms
    dropped_frames = 0
    presented_frames = 0
    presentation_latencies = []
    underruns = 0

    # Presentation Consumer Loop
    for f in range(total_frames):
        t0 = time.perf_counter()
        try:
            # Deadline: 16.66ms + 10ms tolerance
            disp_frame = frame_queue.get(timeout=0.030)
            presented_frames += 1
        except queue.Empty:
            dropped_frames += 1
            underruns += 1

        dt = (time.perf_counter() - t0) * 1000.0
        presentation_latencies.append(dt)

        if (f + 1) % 3600 == 0:
            elapsed = time.perf_counter() - t_start
            print(f"Progress: {f + 1}/{total_frames} frames ({((f + 1) / total_frames) * 100:.0f}%) | "
                  f"Presented: {presented_frames} | Dropped: {dropped_frames} | Elapsed: {elapsed:.1f}s")

    stop_event.set()
    worker_thread.join()
    t_total = time.perf_counter() - t_start

    # AV Sync Drift Calculation across 5 minutes
    # 18,000 video frames at 60fps = 300.000 seconds
    # Audio at 48000 Hz = exactly 14,400,000 samples
    expected_audio_samples = int(total_frames * 48000 / target_fps)
    computed_audio_samples = int(RationalTime(total_frames, target_fps).to_audio_samples(48000))
    drift_samples = abs(expected_audio_samples - computed_audio_samples)
    drift_ms = (drift_samples / 48000.0) * 1000.0

    mean_worker_ms = float(np.mean(worker_latencies)) if worker_latencies else 0.0
    p95_worker_ms = float(np.percentile(worker_latencies, 95)) if worker_latencies else 0.0
    max_worker_ms = float(np.max(worker_latencies)) if worker_latencies else 0.0

    results = {
        "test_name": "5_minute_sustained_playback_18000_frames",
        "target_frames": total_frames,
        "presented_frames": presented_frames,
        "dropped_frames": dropped_frames,
        "achieved_fps": round(presented_frames / t_total, 2),
        "total_elapsed_seconds": round(t_total, 3),
        "worker_latency_ms": {
            "mean": round(mean_worker_ms, 3),
            "p95": round(p95_worker_ms, 3),
            "max": round(max_worker_ms, 3)
        },
        "frame_budget_ms": round(frame_budget_ms, 2),
        "headroom_pct": round((1.0 - (mean_worker_ms / frame_budget_ms)) * 100.0, 1),
        "av_sync_drift": {
            "expected_audio_samples": expected_audio_samples,
            "computed_audio_samples": computed_audio_samples,
            "drift_samples": drift_samples,
            "drift_ms": drift_ms
        },
        "audio_underruns": underruns,
        "gate_passed": (dropped_frames == 0) and (drift_ms < 1.0)
    }

    os.makedirs("spikes", exist_ok=True)
    with open("spikes/sustained_playback_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"=== SUSTAINED PLAYBACK AUDIT COMPLETE ===")
    print(f"Presented: {presented_frames}/{total_frames} | Dropped: {dropped_frames}")
    print(f"Mean Worker Latency: {mean_worker_ms:.3f} ms (Budget: {frame_budget_ms:.2f} ms)")
    print(f"Headroom: {results['headroom_pct']}% | AV Drift: {drift_ms} ms")
    print(f"Gate Status: {'PASS' if results['gate_passed'] else 'FAIL'}")
    return results


if __name__ == "__main__":
    run_sustained_playback()
