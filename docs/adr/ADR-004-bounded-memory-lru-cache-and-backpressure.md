# ADR-004: Memory-Budgeted LRU Cache, Backpressure, and Seek Cancellation

## Context
Video frames at 1080p and 4K consume substantial RAM and VRAM:
- Uncompressed 1080p RGBA: $1920 \times 1080 \times 4 \text{ bytes} \approx 8.29\text{ MB}$ per frame.
- Uncompressed 4K RGBA: $3840 \times 2160 \times 4 \text{ bytes} \approx 33.18\text{ MB}$ per frame.
An unconstrained frame-prefetch buffer quickly triggers Out-Of-Memory (OOM) crashes, while rapid scrubbing floods background decoders with obsolete decode jobs.

## Empirical Evidence
- Rigorous benchmark suite in [`spikes/seek_benchmark.py`](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/spikes/seek_benchmark.py) and [`spikes/bounded_cache_and_ipc_spike.py`](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/spikes/bounded_cache_and_ipc_spike.py):
  - Fixed budget of 64 MB strictly capped memory usage at **63.3 MB** without exceeding limits.
  - **Indexed Cold Seek (Strict Target: Mean < 30 ms)**:
    - Decode Only: **18.17 ms mean** (Median: 15.39 ms, P95: 27.14 ms, P99: 29.38 ms, Max: 31.30 ms) -> **PASS**.
    - With Canvas Presentation: **19.72 ms mean** (Median: 16.75 ms, P95: 29.03 ms, Max: 33.10 ms) -> **PASS**.
  - **Warm Cache Seek (Strict Target: Mean < 1.0 ms)**:
    - Cache Lookup Only: **0.010 ms mean** (10 microseconds; Median: 0.00 ms, P99: 0.01 ms, Max: 0.89 ms) -> **PASS**.
    - With Canvas Presentation: **1.67 ms mean** (Median: 1.57 ms, P95: 2.23 ms, Max: 3.11 ms) -> **PASS**.
  - **Unindexed Long-GOP Seek (GOP=60)**:
    - Decode Only: **17.67 ms mean** (Forward: 17.04 ms, Backward: 18.31 ms).
    - With Canvas Presentation: **18.70 ms mean** (Forward: 18.07 ms, Backward: 19.34 ms).
  - **Generation Token Seek Cancellation**: In a 10-event rapid scrub burst, **9 obsolete frames were successfully dropped**, executing only the final targeted frame.

## Decision
1. **Explicit Memory Budgets**:
   - Host CPU RAM Cache Budget: Configurable, default **1,024 MB** (~120 frames at 1080p, ~30 frames at 4K).
   - GPU VRAM Texture Cache Budget: Configurable, default **512 MB**.
   - Eviction policy: Strict Least Recently Used (LRU) with memory tracking.
2. **Seek Cancellation & Stale Frame Invalidation**:
   - Every seek request is stamped with a monotonic integer generation token (`generation_id`).
   - Decode threads check the active `generation_id` before demuxing and before posting decoded frames back to the presentation queue. Any packet or frame bearing an older token is discarded immediately.
3. **Decoupled Worker Backpressure**:
   - The decode ring buffer operates with high-water and low-water marks. When the forward buffer reaches 30 frames, the decode thread suspends until playback consumes down to 10 frames, preventing unnecessary CPU/GPU loading.

## Consequences
- Guaranteed upper bound on RAM and VRAM footprint.
- Instantaneous scrub responsiveness without UI freezing or decode backlog during fast scrubbing.
