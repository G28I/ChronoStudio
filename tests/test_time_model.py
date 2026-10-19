"""
tests/test_time_model.py — Unit Tests for Rational Time, Drop-Frame & Editorial Semantics
"""

from fractions import Fraction
import pytest
from core.time_model import RationalTime, TimeRange, ClipItem


def test_rational_arithmetic_precision():
    # 23.976 fps is exactly 24000/1001
    rate_23976 = Fraction(24000, 1001)
    t1 = RationalTime(24000, rate_23976) # Exactly 1001 seconds
    assert t1.to_seconds_fraction() == 1001
    assert t1.to_seconds() == 1001.0

    # Addition across different rates
    t_60 = RationalTime(60, 60) # 1.0 second
    t_30 = RationalTime(30, 30) # 1.0 second
    t_sum = t_60 + t_30
    assert t_sum.to_seconds() == 2.0
    assert t_sum.value == 120
    assert t_sum.rate == Fraction(60, 1)


def test_drop_frame_timecode():
    rate_2997 = Fraction(30000, 1001)
    
    # 0 frames -> 00:00:00;00
    t0 = RationalTime(0, rate_2997)
    assert t0.to_timecode(drop_frame=True) == "00:00:00;00"

    # Frame 1799 (just before minute 1, 1800 frames nominal)
    t_1799 = RationalTime(1799, rate_2997)
    # Minute 1 drops frames .00 and .01, so frame 1800 should be labeled 00:01:00;02
    t_1800 = RationalTime(1800, rate_2997)
    assert t_1800.to_timecode(drop_frame=True) == "00:01:00;02"

    # 10th minute (minute 10 does NOT drop frames)
    # 10 minutes = 17982 frames in 29.97 DF
    t_10min = RationalTime(17982, rate_2997)
    assert t_10min.to_timecode(drop_frame=True) == "00:10:00;00"


def test_half_open_interval_abutment():
    rate = 60
    # Clip 1: [0, 100) -> 100 frames
    r1 = TimeRange(RationalTime(0, rate), RationalTime(100, rate))
    # Clip 2: [100, 250) -> 150 frames
    r2 = TimeRange(RationalTime(100, rate), RationalTime(150, rate))

    assert r1.end == r2.start
    assert not r1.overlaps(r2)
    assert r1.contains(RationalTime(0, rate))
    assert r1.contains(RationalTime(99, rate))
    assert not r1.contains(RationalTime(100, rate)) # exclusive end
    assert r2.contains(RationalTime(100, rate)) # inclusive start


def test_clip_split_conservation():
    rate = 60
    # Original clip: 300 frames on timeline [100, 400), source_in = 500
    orig_range = TimeRange(RationalTime(100, rate), RationalTime(300, rate))
    clip = ClipItem("c1", "a1", orig_range, source_in=RationalTime(500, rate))

    # Split at frame 250
    split_pt = RationalTime(250, rate)
    head, tail = clip.split(split_pt)

    assert head is not None and tail is not None
    # Conservation of timeline duration
    assert head.timeline_range.duration.value + tail.timeline_range.duration.value == 300
    assert head.timeline_range.start.value == 100
    assert head.timeline_range.end.value == 250
    assert tail.timeline_range.start.value == 250
    assert tail.timeline_range.end.value == 400

    # Source continuity
    assert head.source_in.value == 500
    assert head.source_out.value == 650
    assert tail.source_in.value == 650
    assert tail.source_out.value == 800


def test_slip_and_slide_mechanics():
    rate = 60
    r = TimeRange(RationalTime(100, rate), RationalTime(60, rate))
    clip = ClipItem("c1", "a1", r, source_in=RationalTime(1000, rate))

    # Slip +20 frames: timeline position stays [100, 160), source moves to [1020, 1080)
    slipped = clip.slip(RationalTime(20, rate))
    assert slipped.timeline_range.start.value == 100
    assert slipped.timeline_range.duration.value == 60
    assert slipped.source_in.value == 1020
    assert slipped.source_out.value == 1080

    # Slide -30 frames: timeline moves to [70, 130), source stays at 1000
    slid = clip.slide(RationalTime(-30, rate))
    assert slid.timeline_range.start.value == 70
    assert slid.timeline_range.duration.value == 60
    assert slid.source_in.value == 1000


def test_audio_sample_accuracy_and_long_sequence():
    # Long sequence: 1,000,000 frames at 23.976 fps (~11.58 hours)
    rate_video = Fraction(24000, 1001)
    t_end = RationalTime(1000000, rate_video)

    # Convert to 48kHz audio samples
    audio_samples = t_end.to_audio_samples(48000)
    # 1,000,000 * 1001 / 24000 * 48000 = 1,000,000 * 2002 = 2,002,000,000 samples exactly
    assert audio_samples == 2002000000

    # Re-convert back to video rate
    t_reconstructed = RationalTime(audio_samples, 48000).rescale(rate_video)
    assert t_reconstructed.value == 1000000
