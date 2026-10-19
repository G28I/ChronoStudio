"""
core/media_importer.py — Media Ingest, Stream Metadata Extraction & Missing-Media Handling
Extracts exact container and stream attributes via PyAV / FFmpeg,
and provides offline placeholder generation when media is disconnected.
"""

import os
from fractions import Fraction
from typing import Dict, Any, Optional
import av
import numpy as np
from PIL import Image, ImageDraw


class MediaAsset:
    def __init__(self, asset_id: str, file_path: str, metadata: Dict[str, Any]):
        self.asset_id = asset_id
        self.file_path = os.path.abspath(file_path)
        self.metadata = metadata
        self.is_offline = not os.path.exists(self.file_path)

    @property
    def has_video(self) -> bool:
        return self.metadata.get("video") is not None

    @property
    def has_audio(self) -> bool:
        return self.metadata.get("audio") is not None

    @property
    def duration_seconds(self) -> float:
        return float(self.metadata.get("duration_seconds", 0.0))

    @property
    def video_fps(self) -> Fraction:
        if self.has_video:
            return self.metadata["video"]["fps"]
        return Fraction(60, 1)

    @property
    def video_resolution(self) -> tuple[int, int]:
        if self.has_video:
            return (self.metadata["video"]["width"], self.metadata["video"]["height"])
        return (1920, 1080)


class MediaImporter:
    def __init__(self):
        self.asset_registry: Dict[str, MediaAsset] = {}

    def import_asset(self, asset_id: str, file_path: str) -> MediaAsset:
        """
        Inspects container and streams.
        Gracefully handles existing or missing media.
        """
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            # Missing media: create offline placeholder metadata
            meta = {
                "file_path": abs_path,
                "is_offline": True,
                "duration_seconds": 10.0,
                "video": {
                    "width": 1920,
                    "height": 1080,
                    "fps": Fraction(60, 1),
                    "codec": "offline_placeholder",
                    "pixel_format": "rgba"
                },
                "audio": {
                    "sample_rate": 48000,
                    "channels": 2,
                    "codec": "offline_silence"
                }
            }
            asset = MediaAsset(asset_id, abs_path, meta)
            self.asset_registry[asset_id] = asset
            return asset

        # Real media: probe container via PyAV
        container = av.open(abs_path)
        meta = {
            "file_path": abs_path,
            "is_offline": False,
            "format_name": container.format.name,
            "duration_seconds": float(container.duration / av.time_base) if container.duration else 0.0,
            "video": None,
            "audio": None
        }

        if len(container.streams.video) > 0:
            v = container.streams.video[0]
            fps = v.average_rate
            if not fps or fps == 0:
                fps = Fraction(60, 1)
            meta["video"] = {
                "width": v.width,
                "height": v.height,
                "fps": Fraction(fps.numerator, fps.denominator),
                "codec": v.codec_context.name,
                "pixel_format": v.codec_context.pix_fmt,
                "frames": v.frames or int(round(meta["duration_seconds"] * float(fps)))
            }

        if len(container.streams.audio) > 0:
            a = container.streams.audio[0]
            meta["audio"] = {
                "sample_rate": a.sample_rate or 48000,
                "channels": a.channels or 2,
                "codec": a.codec_context.name,
                "channel_layout": a.layout.name if a.layout else "stereo"
            }

        container.close()
        asset = MediaAsset(asset_id, abs_path, meta)
        self.asset_registry[asset_id] = asset
        return asset

    def generate_offline_placeholder(self, asset: MediaAsset, frame_idx: int) -> np.ndarray:
        """
        Renders a standard 'MEDIA OFFLINE' red/black graphic frame
        to guarantee the preview pipeline never crashes on missing media.
        """
        w, h = asset.video_resolution
        img = Image.new("RGBA", (w, h), (20, 20, 25, 255))
        draw = ImageDraw.Draw(img)

        # Draw red border warning box
        draw.rectangle([40, 40, w - 40, h - 40], outline=(220, 40, 40, 255), width=6)
        # Draw diagonals
        draw.line([40, 40, w - 40, h - 40], fill=(120, 20, 20, 180), width=3)
        draw.line([40, h - 40, w - 40, 40], fill=(120, 20, 20, 180), width=3)

        # Center banner
        draw.rectangle([w // 2 - 300, h // 2 - 60, w // 2 + 300, h // 2 + 60], fill=(180, 20, 20, 230))
        text = f"MEDIA OFFLINE\n{os.path.basename(asset.file_path)}"
        draw.text((w // 2, h // 2), text, fill=(255, 255, 255, 255), anchor="mm")

        return np.array(img, dtype=np.uint8)
