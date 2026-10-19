"""
core/timeline_model.py — Multi-Track Sequence Model with Razor Cuts, Trimming, Snapping & Ripple Delete
Enforces exact RationalTime half-open interval boundaries [start, end).
"""

from fractions import Fraction
from typing import Dict, List, Optional, Tuple, Any
from core.time_model import RationalTime, TimeRange, ClipItem


class Track:
    def __init__(self, track_id: str, kind: str, name: Optional[str] = None):
        self.track_id = track_id
        self.kind = kind  # "video" or "audio"
        self.name = name or track_id
        self.locked = False
        self.muted = False
        self.solo = False
        self.clips: List[ClipItem] = []

    def add_clip(self, clip: ClipItem) -> None:
        """Adds a clip to the track, keeping clips sorted by timeline start time."""
        # Check for overlaps
        for existing in self.clips:
            if existing.timeline_range.overlaps(clip.timeline_range):
                raise ValueError(f"Clip overlap detected on track {self.track_id} between {existing.clip_id} and {clip.clip_id}")
        self.clips.append(clip)
        self.clips.sort(key=lambda c: c.timeline_range.start.value)

    def find_clip_by_id(self, clip_id: str) -> Optional[ClipItem]:
        for c in self.clips:
            if c.clip_id == clip_id:
                return c
        return None

    def get_clip_at(self, t: RationalTime) -> Optional[ClipItem]:
        for c in self.clips:
            if c.timeline_range.contains(t):
                return c
        return None

    def split_clip(self, clip_id: str, at_time: RationalTime) -> Tuple[Optional[ClipItem], Optional[ClipItem]]:
        """Splits clip into head and tail."""
        clip = self.find_clip_by_id(clip_id)
        if not clip:
            return None, None
        head, tail = clip.split(at_time)
        if tail is not None:
            self.clips.remove(clip)
            self.clips.append(head)
            self.clips.append(tail)
            self.clips.sort(key=lambda c: c.timeline_range.start.value)
        return head, tail

    def trim_clip(self, clip_id: str, edge: str, delta: RationalTime) -> ClipItem:
        """Trims head or tail of a clip."""
        clip = self.find_clip_by_id(clip_id)
        if not clip:
            raise ValueError(f"Clip {clip_id} not found on track {self.track_id}")
        self.clips.remove(clip)
        if edge == "in":
            trimmed = clip.trim_in(delta)
        elif edge == "out":
            trimmed = clip.trim_out(delta)
        else:
            raise ValueError(f"Unknown trim edge: {edge}")
        self.add_clip(trimmed)
        return trimmed

    def ripple_delete(self, clip_id: str) -> RationalTime:
        """
        Deletes the clip and ripples all subsequent clips to the left
        by the duration of the deleted clip.
        Returns the duration that was rippled.
        """
        clip = self.find_clip_by_id(clip_id)
        if not clip:
            raise ValueError(f"Clip {clip_id} not found on track {self.track_id}")
        
        idx = self.clips.index(clip)
        dur = clip.timeline_range.duration
        self.clips.remove(clip)

        # Shift subsequent clips left by dur
        new_clips = []
        for c in self.clips[idx:]:
            new_start = c.timeline_range.start - dur
            shifted = ClipItem(c.clip_id, c.asset_id, TimeRange(new_start, c.timeline_range.duration), c.source_in)
            new_clips.append(shifted)
        
        self.clips = self.clips[:idx] + new_clips
        return dur


class TimelineModel:
    def __init__(self, sequence_id: str = "seq_01", timebase_rate: Fraction | int = 60):
        self.sequence_id = sequence_id
        if isinstance(timebase_rate, int):
            timebase_rate = Fraction(timebase_rate, 1)
        self.timebase_rate = timebase_rate
        self.video_tracks: Dict[str, Track] = {
            "V1": Track("V1", "video"),
            "V2": Track("V2", "video")
        }
        self.audio_tracks: Dict[str, Track] = {
            "A1": Track("A1", "audio"),
            "A2": Track("A2", "audio")
        }

    @property
    def duration(self) -> RationalTime:
        max_end = RationalTime(0, self.timebase_rate)
        for trk in list(self.video_tracks.values()) + list(self.audio_tracks.values()):
            for c in trk.clips:
                if c.timeline_range.end > max_end:
                    max_end = c.timeline_range.end
        return max_end

    def add_clip(self, track_id: str, clip: ClipItem) -> None:
        if track_id in self.video_tracks:
            self.video_tracks[track_id].add_clip(clip)
        elif track_id in self.audio_tracks:
            self.audio_tracks[track_id].add_clip(clip)
        else:
            raise ValueError(f"Track {track_id} does not exist in timeline")

    def split_clip(self, clip_id: str, at_time: RationalTime) -> Tuple[Optional[ClipItem], Optional[ClipItem]]:
        for trk in list(self.video_tracks.values()) + list(self.audio_tracks.values()):
            if trk.find_clip_by_id(clip_id):
                return trk.split_clip(clip_id, at_time)
        return None, None

    def ripple_delete(self, track_id: str, clip_id: str) -> RationalTime:
        if track_id in self.video_tracks:
            return self.video_tracks[track_id].ripple_delete(clip_id)
        elif track_id in self.audio_tracks:
            return self.audio_tracks[track_id].ripple_delete(clip_id)
        raise ValueError(f"Track {track_id} not found")

    def snap_time(self, t: RationalTime, tolerance_frames: int = 4) -> RationalTime:
        """
        Magnetic snapping: if t is within tolerance of any clip in/out point,
        returns the snapped time. Otherwise returns t.
        """
        target_val = t.rescale(self.timebase_rate).value
        best_diff = tolerance_frames + 1
        best_val = target_val

        # Collect all edit points
        points = [0]
        for trk in list(self.video_tracks.values()) + list(self.audio_tracks.values()):
            for c in trk.clips:
                points.append(c.timeline_range.start.rescale(self.timebase_rate).value)
                points.append(c.timeline_range.end.rescale(self.timebase_rate).value)

        for p in points:
            diff = abs(target_val - p)
            if diff <= tolerance_frames and diff < best_diff:
                best_diff = diff
                best_val = p

        return RationalTime(best_val, self.timebase_rate)

    def get_active_clips_at(self, t: RationalTime) -> Dict[str, Optional[ClipItem]]:
        """Returns map of track_id -> active ClipItem at timeline time t."""
        active = {}
        for tid, trk in self.video_tracks.items():
            if not trk.muted:
                active[tid] = trk.get_clip_at(t)
        for tid, trk in self.audio_tracks.items():
            if not trk.muted:
                active[tid] = trk.get_clip_at(t)
        return active
