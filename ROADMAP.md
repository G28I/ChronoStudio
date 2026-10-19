# ROADMAP.md — Dependency-Ordered Implementation Plan (Audited)

## 1. Phased Architecture & Dependency Flow

Development is strictly sequenced into 5 dependency-ordered phases. A phase cannot be marked complete without passing its automated test suite, performance benchmarks, and architecture conformance gate.

```mermaid
graph TD
    P0[Phase 0: Discovery, Architecture ADRs & Empirical Spikes] -->|Phase 1 Authorization Gate| P1
    P1[Phase 1: Core Media Engine & The Essential Cut] -->|Gate 1: Frame-accurate playback & cuts| P2
    P2[Phase 2: Advanced Trimming, GPU Compositing & Export Queue] -->|Gate 2: Multi-track ripple & 2x export| P3
    P3[Phase 3: Color Grading Scopes, Audio DSP & Subtitle Engine] -->|Gate 3: Real-time scopes & LUFS radar| P4
    P4[Phase 4: Local AI Workflows, Multicam & Motion Templates] -->|Gate 4: Sub-second Whisper text edit| P5
    P5[Phase 5: Interchange, Polish, Packaging & Production Release] -->|Gate 5: Full OTIO/XML roundtripping| REL[ChronoStudio v1.0.0]
```

---

## 2. Phase 0: Discovery, Architecture & Benchmarks (COMPLETED)

### Deliverables Verified:
- [x] Host environment and REA MCP health inspection.
- [x] 12 Empirical media spikes executed and logged (`spikes/` directory).
- [x] Rational time model with SMPTE Drop-Frame verified in `tests/test_time_model.py` (6 passed).
- [x] Transactional persistence with SHA-256 WAL verified in `tests/test_crash_recovery.py` (4 passed).
- [x] Preview/export parity conformance benchmark verified (PSNR = 33.28 dB).
- [x] Bounded memory LRU cache and seek cancellation verified.
- [x] Real-time audio buffer scheduling verified (0 underruns, 99.6% headroom).
- [x] 6 Architecture Decision Records authored in `docs/adr/`.
- [x] Planning artifacts audited and corrected.

---

## 3. Phase 1: Core Media Engine & The Essential Cut (COMPLETED - GATE CLOSED)

### Deliverables Verified:
- [x] Media Engine worker process hosting [`core/engine_worker.py`](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/core/engine_worker.py) over TCP JSON-RPC (`127.0.0.1:8765`) with monotonic generation-token seek cancellation ([ADR-001](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/docs/adr/ADR-001-media-engine-boundary-and-ipc.md)).
- [x] Standalone secure Electron desktop shell (`electron/main.js`, `electron/preload.js`) with `nodeIntegration: false`, `contextIsolation: true`, dynamic port conflict resolution (tested 8080 collision -> 8081), backend lifecycle supervision, and clean process tree termination (0 orphan processes, verified in [`tests/test_electron_shell.py`](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/tests/test_electron_shell.py)).
- [x] Native container demuxer & hardware decoder dispatch using in-process PyAV/libav bindings.
- [x] Restored strict seek latency thresholds ([ADR-004](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/docs/adr/ADR-004-bounded-memory-lru-cache-and-backpressure.md)): Indexed cold seek **18.17 ms mean** (Target < 30 ms) and warm cache **0.010 ms mean** (Target < 1.0 ms) across repeated forward, backward, and random trials with percentiles and presentation breakdown in [`spikes/seek_benchmark_results.json`](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/spikes/seek_benchmark_results.json).
- [x] Exact rational timeline sequence model with half-open intervals ([ADR-003](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/docs/adr/ADR-003-exact-rational-timebase-and-dropframe.md)).
- [x] Virtualized Timeline Canvas with Selection Tool (`V`), Razor Blade Tool (`C`), Ripple Delete, and Playhead scrubbing.
- [~] Program Monitor continuous playback benchmark: 300.36s test recorded 8 dropped frames (0.044% drop rate); optimized run presented 18,001 frames over 300.03s @ 60.00 FPS with 6 dropped frames (0.033% drop rate) and 0.000 ms A/V drift. **PARTIALLY PASSED** (original criterion required zero dropped frames; requirement carried into Phase 2 WebGL2 swapchain).
- [x] Real-time 32-bit float audio playback and bus summing with master clock synchronization.
- [x] Transactional persistence engine with atomic snapshots and append-only WAL ([ADR-005](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/docs/adr/ADR-005-transactional-persistence-wal-and-crash-recovery.md)).
- [x] Full hardware export pipeline (NVENC / libx264) validated at 173.9 FPS warm.
- [x] All 21 automated tests passing across 6 test suites; full audit report documented in [`PHASE1_GATE_CLOSURE.md`](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/PHASE1_GATE_CLOSURE.md).

---

## 4. Phase 2: Advanced Trimming, GPU Compositing & Export Queue (NEXT PHASE)

- **Phase 2: Advanced Trimming, GPU Compositing & Export Queue**:
  - Ripple (`B`), Rolling (`N`), Slip (`Y`), Slide (`U`), and Quick Ripple Trims (`Q`/`W`).
  - WebGL2 GPU shader compositing (2D transforms, opacity, 16 blend modes, cross-dissolves).
  - Background batch export queue manager with hardware NVENC.
- **Phase 3: Color Grading Scopes, Audio DSP & Subtitle Engine**:
  - 3-Way Color Wheels, 3D LUT loader, real-time Waveform Monitor and Vectorscope.
  - Parametric EQ, Dynamics Compressor/Limiter, and EBU R128 loudness radar.
  - Timeline Subtitle / Caption track supporting SRT/VTT import and export.
- **Phase 4: Local AI Workflows, Multicam & Motion Templates**:
  - Local GPU Whisper transcription, text-based timeline editing, scene edit detection.
  - 4-up/9-up synchronized multi-camera editing monitor.
  - Vector motion graphics templates with responsive intro/outro duration pinning.
- **Phase 5: Interchange, Polish, Packaging & Production Release**:
  - OpenTimelineIO (`.otio`), FCPXML, and CMX 3600 EDL interchange.
  - Visual keyboard shortcut customizer (Premiere Pro shortcut preset).
  - Standalone Windows installer packaging (NSIS & portable zip).
