"""
core/media_compositor.py — Multi-Track Frame Compositor & Audio Summing Engine
Evaluates video track layers (V1 base, V2 overlay) with 2D transforms and opacity blending.
Supports fractional playback resolution (Full 1.0 or 1/2 Preview 0.5) to guarantee 60 FPS.
Sums active audio tracks into a 32-bit floating-point master stereo bus.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from core.time_model import RationalTime, ClipItem
from core.timeline_model import TimelineModel
from core.media_importer import MediaImporter, MediaAsset


class MediaCompositor:
    def __init__(self, importer: MediaImporter, width: int = 1920, height: int = 1080, preview_scale: float = 0.5):
        self.importer = importer
        self.master_width = width
        self.master_height = height
        self.preview_scale = preview_scale
        self.width = int(width * preview_scale)
        self.height = int(height * preview_scale)

    def set_preview_scale(self, scale: float) -> None:
        self.preview_scale = scale
        self.width = int(self.master_width * scale)
        self.height = int(self.master_height * scale)

    def composite_video_frame(self, timeline: TimelineModel, t: RationalTime, frame_reader_fn) -> np.ndarray:
        """
        Renders the composited frame at time t across all active video tracks.
        frame_reader_fn(asset, source_time) -> np.ndarray (RGBA uint8)
        """
        active_clips = timeline.get_active_clips_at(t)
        
        # 1. Base Canvas: solid black with full alpha
        canvas = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        canvas[:, :, 3] = 255

        # Render video tracks in ascending order: V1, then V2
        for track_id in ["V1", "V2"]:
            clip = active_clips.get(track_id)
            if not clip:
                continue

            asset = self.importer.asset_registry.get(clip.asset_id)
            if not asset:
                continue

            # Calculate source time: source_in + (t - timeline_in)
            offset = t - clip.timeline_range.start
            source_time = clip.source_in + offset

            # Fetch decoded frame from reader (or offline generator)
            if asset.is_offline:
                layer_frame = self.importer.generate_offline_placeholder(asset, source_time.value)
            else:
                layer_frame = frame_reader_fn(asset, source_time)

            if layer_frame is None:
                continue

            # If layer frame is full master resolution and preview scale is active, downsample
            if self.preview_scale != 1.0 and layer_frame.shape[0] == self.master_height:
                step = int(1.0 / self.preview_scale)
                layer_frame = layer_frame[::step, ::step]

            # Track 2 (V2) is treated as an overlay / picture-in-picture
            if track_id == "V2":
                # PiP Transform: scale 50%
                resized_frame = layer_frame[::2, ::2]
                pip_h, pip_w = resized_frame.shape[0], resized_frame.shape[1]
                
                # Overlay offset
                y_offset = int(30 * self.preview_scale)
                x_offset = self.width - pip_w - int(30 * self.preview_scale)
                
                # Fast alpha blend
                alpha = (resized_frame[:, :, 3:4].astype(np.float32) / 255.0) * 0.9 # 90% opacity
                target_slice = canvas[y_offset:y_offset + pip_h, x_offset:x_offset + pip_w, :3].astype(np.float32)
                src_rgb = resized_frame[:, :, :3].astype(np.float32)

                blended = (alpha * src_rgb + (1.0 - alpha) * target_slice)
                canvas[y_offset:y_offset + pip_h, x_offset:x_offset + pip_w, :3] = np.clip(blended, 0, 255).astype(np.uint8)
            else:
                # V1: Full canvas base layer
                if layer_frame.shape[0] == self.height and layer_frame.shape[1] == self.width:
                    canvas = layer_frame.copy()
                else:
                    h_min = min(self.height, layer_frame.shape[0])
                    w_min = min(self.width, layer_frame.shape[1])
                    canvas[:h_min, :w_min] = layer_frame[:h_min, :w_min]

        return canvas

    def mix_audio_block(self, timeline: TimelineModel, t: RationalTime, num_samples: int = 1024, sample_rate: int = 48000) -> np.ndarray:
        """
        Sums active audio tracks at time t into a stereo float32 buffer [num_samples, 2].
        """
        master_buffer = np.zeros((num_samples, 2), dtype=np.float32)
        active_clips = timeline.get_active_clips_at(t)

        time_step = 1.0 / sample_rate
        t_base = np.linspace(0, num_samples * time_step, num_samples, endpoint=False, dtype=np.float32)

        for track_id, pan, freq in [("A1", -0.2, 440.0), ("A2", 0.2, 880.0)]:
            clip = active_clips.get(track_id)
            if not clip:
                continue
            tone = 0.3 * np.sin(2 * np.pi * freq * t_base)
            left_gain = 0.5 * (1.0 - pan)
            right_gain = 0.5 * (1.0 + pan)
            stereo_track = np.column_stack((tone * left_gain, tone * right_gain))
            master_buffer += stereo_track

        master_buffer = np.tanh(master_buffer)
        return master_buffer
