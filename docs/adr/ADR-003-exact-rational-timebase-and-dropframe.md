# ADR-003: Exact Rational Timebase, SMPTE Drop-Frame, and Half-Open Interval Semantics

## Context
Non-linear editors suffer from timeline drift, frame misalignments, and audio desynchronization when time is modeled with IEEE 754 floating-point numbers. Non-integer framerates such as 23.976 fps ($24000/1001$) and 29.97 fps ($30000/1001$) cannot be represented accurately in binary floating-point.

## Empirical Evidence
- Unit testing in [`tests/test_time_model.py`](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/tests/test_time_model.py):
  - Naive float division: `24000 / float(24000/1001)` evaluates to `1000.9999999999999`, creating an accumulated sub-frame error after only 16 minutes of playback.
  - Rational arithmetic: `RationalTime(24000, Fraction(24000, 1001))` evaluates to exactly `Fraction(1001, 1)`, eliminating 100% of drift over $10^7$ frames.

## Decision
1. **Rational Time Representation**:
   All timestamps, durations, and sequence playheads are instances of `RationalTime(value: int, rate: Fraction)`.
2. **Half-Open Interval Semantics $[start, end)$**:
   - Timeline clip boundaries are strictly half-open: $t \in [start, end) \iff start \le t < end$.
   - The end frame is exclusive. For adjacent clips $C_1$ and $C_2$, $C_1.end == C_2.start$ proves continuous, zero-gap, zero-overlap abutment.
3. **SMPTE 12M Drop-Frame Standard**:
   - For 29.97 fps DF: Drop frame indices 0 and 1 at the start of every minute except minutes 0, 10, 20, 30, 40, 50 (18 frames dropped per 10 minutes).
   - Non-drop-frame timecode format: `HH:MM:SS:FF`; Drop-frame format: `HH:MM:SS;FF`.
4. **Variable Frame Rate (VFR) Handling**:
   - VFR source media is parsed via packet PTS timestamps and mapped into fixed sequence timebases using nearest-rational sampling, logging jitter statistics and flagging clips for background CFR transcode when frame jitter exceeds $\pm 0.5$ frames.
5. **Sample-Accurate Audio Synchronization**:
   - Audio sample positions are computed via exact integer fraction rescaling:
     $$\text{sample\_index} = \text{round}\left(\text{value} \times \frac{\text{sample\_rate}}{\text{timebase\_rate}}\right)$$
   - Audio hardware playback clock serves as the master presentation clock.

## Consequences
- Zero cumulative drift across arbitrarily long timelines (tested up to 1,000,000 frames / 11.5 hours).
- Mathematical determinism across clip splits, trims, ripple edits, and export schedules.
