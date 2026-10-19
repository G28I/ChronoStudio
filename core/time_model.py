"""
core/time_model.py — Authoritative Frame-Accurate Rational Time Model
Implements SMPTE 12M Non-Drop-Frame (NDF) and Drop-Frame (DF) timecodes,
half-open interval semantics [start, end), mixed-rate conversions,
and audio sample-accurate synchronization.
"""

from fractions import Fraction
import math
from typing import Tuple, Optional


class RationalTime:
    """
    Exact rational representation of a point in time or duration.
    Eliminates floating-point accumulation errors.
    time_in_seconds = value / rate
    """
    __slots__ = ("_value", "_rate")

    def __init__(self, value: int, rate: Fraction | int):
        if isinstance(rate, int):
            if rate <= 0:
                raise ValueError("Rate must be positive")
            self._rate = Fraction(rate, 1)
        elif isinstance(rate, Fraction):
            if rate <= 0:
                raise ValueError("Rate must be positive")
            self._rate = rate
        else:
            raise TypeError("Rate must be an int or fractions.Fraction")
        self._value = int(value)

    @property
    def value(self) -> int:
        return self._value

    @property
    def rate(self) -> Fraction:
        return self._rate

    def to_seconds_fraction(self) -> Fraction:
        return Fraction(self._value) / self._rate

    def to_seconds(self) -> float:
        return float(Fraction(self._value) / self._rate)

    def rescale(self, new_rate: Fraction | int, rounding: str = "nearest") -> "RationalTime":
        """
        Rescale this time to a new timebase rate.
        rounding: 'nearest', 'floor', or 'ceil'
        """
        if isinstance(new_rate, int):
            new_rate = Fraction(new_rate, 1)
        if self._rate == new_rate:
            return RationalTime(self._value, self._rate)

        # Exact rational value in new timebase units
        raw_val = Fraction(self._value) * new_rate / self._rate
        if rounding == "floor":
            new_val = math.floor(raw_val)
        elif rounding == "ceil":
            new_val = math.ceil(raw_val)
        elif rounding == "nearest":
            # Round half up / round to nearest integer
            new_val = round(raw_val)
        else:
            raise ValueError(f"Unknown rounding mode: {rounding}")
        return RationalTime(int(new_val), new_rate)

    def to_audio_samples(self, sample_rate: int = 48000) -> int:
        """Returns exact sample index at given audio sample rate."""
        rescaled = self.rescale(sample_rate, rounding="nearest")
        return rescaled.value

    def to_timecode(self, drop_frame: bool = False) -> str:
        """
        Converts to SMPTE HH:MM:SS:FF or HH:MM:SS;FF (drop-frame).
        Standard SMPTE rates supported: 24, 25, 30, 48, 50, 60, 23.976, 29.97, 59.94.
        """
        fps_nominal = round(float(self._rate))
        frame_number = self._value

        if not drop_frame:
            # Non-drop frame calculation
            total_seconds, frames = divmod(frame_number, fps_nominal)
            total_minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(total_minutes, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

        # Drop-Frame SMPTE 12M calculation
        # Supported for 29.97 (30000/1001) and 59.94 (60000/1001)
        if fps_nominal == 30:
            drop_frames = 2
            frames_per_minute = 1800  # 30 * 60
            frames_per_10min = 17982  # 18000 - (9 * 2)
        elif fps_nominal == 60:
            drop_frames = 4
            frames_per_minute = 3600
            frames_per_10min = 35964  # 36000 - (9 * 4)
        else:
            raise ValueError(f"Drop-frame timecode not supported for nominal rate {fps_nominal}")

        d = frame_number // frames_per_10min
        m = frame_number % frames_per_10min

        if m > drop_frames:
            frame_number_adjusted = frame_number + (drop_frames * 9 * d) + drop_frames * ((m - drop_frames) // (frames_per_minute - drop_frames))
        else:
            frame_number_adjusted = frame_number + (drop_frames * 9 * d)

        frames = frame_number_adjusted % fps_nominal
        seconds = (frame_number_adjusted // fps_nominal) % 60
        minutes = ((frame_number_adjusted // fps_nominal) // 60) % 60
        hours = (((frame_number_adjusted // fps_nominal) // 60) // 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d};{frames:02d}"

    def __add__(self, other: "RationalTime") -> "RationalTime":
        if self._rate == other._rate:
            return RationalTime(self._value + other._value, self._rate)
        # Common rate
        common_rate = self._rate
        other_rescaled = other.rescale(common_rate)
        return RationalTime(self._value + other_rescaled.value, common_rate)

    def __sub__(self, other: "RationalTime") -> "RationalTime":
        if self._rate == other._rate:
            return RationalTime(self._value - other._value, self._rate)
        common_rate = self._rate
        other_rescaled = other.rescale(common_rate)
        return RationalTime(self._value - other_rescaled.value, common_rate)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RationalTime):
            return False
        if self._rate == other._rate:
            return self._value == other._value
        return (Fraction(self._value) * other._rate) == (Fraction(other._value) * self._rate)

    def __lt__(self, other: "RationalTime") -> bool:
        if self._rate == other._rate:
            return self._value < other._value
        return (Fraction(self._value) * other._rate) < (Fraction(other._value) * self._rate)

    def __le__(self, other: "RationalTime") -> bool:
        if self._rate == other._rate:
            return self._value <= other._value
        return (Fraction(self._value) * other._rate) <= (Fraction(other._value) * self._rate)

    def __gt__(self, other: "RationalTime") -> bool:
        if self._rate == other._rate:
            return self._value > other._value
        return (Fraction(self._value) * other._rate) > (Fraction(other._value) * self._rate)

    def __ge__(self, other: "RationalTime") -> bool:
        if self._rate == other._rate:
            return self._value >= other._value
        return (Fraction(self._value) * other._rate) >= (Fraction(other._value) * self._rate)

    def __repr__(self) -> str:
        return f"RationalTime({self._value}/{self._rate})"


class TimeRange:
    """
    Half-open interval [start, end) where end is exclusive.
    Guarantees contiguous abutting edits:
    range1.end == range2.start means zero-gap, zero-overlap abutment.
    """
    __slots__ = ("_start", "_duration")

    def __init__(self, start: RationalTime, duration: RationalTime):
        if duration.value < 0:
            raise ValueError("Duration cannot be negative")
        self._start = start
        self._duration = duration.rescale(start.rate)

    @property
    def start(self) -> RationalTime:
        return self._start

    @property
    def duration(self) -> RationalTime:
        return self._duration

    @property
    def end(self) -> RationalTime:
        return self._start + self._duration

    def contains(self, t: RationalTime) -> bool:
        if t.rate == self._start.rate:
            return self._start.value <= t.value < (self._start.value + self._duration.value)
        t_aligned = t.rescale(self._start.rate)
        return self._start <= t_aligned < self.end

    def overlaps(self, other: "TimeRange") -> bool:
        other_start = other.start.rescale(self._start.rate)
        other_end = other.end.rescale(self._start.rate)
        return max(self._start, other_start) < min(self.end, other_end)

    def __repr__(self) -> str:
        return f"TimeRange([{self.start.value} -> {self.end.value}) @ {self.start.rate}fps, dur={self.duration.value})"


class ClipItem:
    """
    Represents a clip placed on a sequence track.
    timeline_range: [timeline_in, timeline_out)
    source_range: [source_in, source_out)
    """
    def __init__(self, clip_id: str, asset_id: str, timeline_range: TimeRange, source_in: RationalTime):
        self.clip_id = clip_id
        self.asset_id = asset_id
        self.timeline_range = timeline_range
        self.source_in = source_in.rescale(timeline_range.start.rate)

    @property
    def source_out(self) -> RationalTime:
        return self.source_in + self.timeline_range.duration

    @property
    def source_range(self) -> TimeRange:
        return TimeRange(self.source_in, self.timeline_range.duration)

    def split(self, split_point: RationalTime) -> Tuple[Optional["ClipItem"], Optional["ClipItem"]]:
        """
        Splits clip into two halves at split_point.
        Returns (head_clip, tail_clip).
        """
        split_aligned = split_point.rescale(self.timeline_range.start.rate)
        if not self.timeline_range.contains(split_aligned) or split_aligned == self.timeline_range.start:
            return (self, None)

        head_dur = split_aligned - self.timeline_range.start
        tail_dur = self.timeline_range.end - split_aligned

        head_clip = ClipItem(
            clip_id=f"{self.clip_id}_head",
            asset_id=self.asset_id,
            timeline_range=TimeRange(self.timeline_range.start, head_dur),
            source_in=self.source_in
        )
        tail_clip = ClipItem(
            clip_id=f"{self.clip_id}_tail",
            asset_id=self.asset_id,
            timeline_range=TimeRange(split_aligned, tail_dur),
            source_in=self.source_in + head_dur
        )
        return (head_clip, tail_clip)

    def trim_in(self, delta_timeline: RationalTime) -> "ClipItem":
        """Ripple/Roll trim head."""
        delta = delta_timeline.rescale(self.timeline_range.start.rate)
        new_start = self.timeline_range.start + delta
        new_dur = self.timeline_range.duration - delta
        new_source_in = self.source_in + delta
        return ClipItem(self.clip_id, self.asset_id, TimeRange(new_start, new_dur), new_source_in)

    def trim_out(self, delta_timeline: RationalTime) -> "ClipItem":
        """Ripple/Roll trim tail."""
        delta = delta_timeline.rescale(self.timeline_range.start.rate)
        new_dur = self.timeline_range.duration + delta
        return ClipItem(self.clip_id, self.asset_id, TimeRange(self.timeline_range.start, new_dur), self.source_in)

    def slip(self, delta_source: RationalTime) -> "ClipItem":
        """Slip edit: adjust source_in/out without moving timeline range."""
        delta = delta_source.rescale(self.timeline_range.start.rate)
        new_source_in = self.source_in + delta
        return ClipItem(self.clip_id, self.asset_id, self.timeline_range, new_source_in)

    def slide(self, delta_timeline: RationalTime) -> "ClipItem":
        """Slide edit: move clip along timeline."""
        delta = delta_timeline.rescale(self.timeline_range.start.rate)
        new_start = self.timeline_range.start + delta
        return ClipItem(self.clip_id, self.asset_id, TimeRange(new_start, self.timeline_range.duration), self.source_in)
