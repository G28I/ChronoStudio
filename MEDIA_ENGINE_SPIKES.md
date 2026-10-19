# MEDIA_ENGINE_SPIKES.md — Empirical Media Engine Proof-of-Concepts (Audited)

This document records the empirical benchmarks executed on the physical Windows workstation (Intel 12th Gen Core i5-12450HX, NVIDIA GeForce RTX 3050 Laptop GPU, 16 GB RAM).

---

## 1. Test Environment & Hardware Inventory

- **Host System**: Windows 11 Desktop (x64)
- **CPU**: 12th Gen Intel Core i5-12450HX (8 cores / 12 threads)
- **Dedicated GPU**: NVIDIA GeForce RTX 3050 6GB Laptop GPU (Driver Version 550+, CUDA 12.x, NVENC/NVDEC)
- **Integrated GPU**: Intel UHD Graphics (QuickSync / QSV enabled)
- **Memory**: 15.7 GB DDR4/DDR5
- **Toolchains**: FFmpeg 8.1.1 (Gyan.dev full build), Python 3.14.7, PyAV 18.1.0, Node.js v24.19.0

---

## 2. Complete Benchmark Inventory & Results

| Spike ID | Domain & Focus | Test Fixture | Measured Results | Architectural Takeaway |
| :--- | :--- | :--- | :--- | :--- |
| **Spike 1** | Media Generation | SMPTE 1080p60 H.264 GOP=30 | Generated in 1.32s | Standardized synthetic test pattern with timecode. |
| **Spike 2** | Raw PTS Seeking | 5s 1080p60 GOP=30 | Mean = **39.61 ms**, Max = **67.94 ms** | Unindexed Long-GOP seeking exceeds 16.6ms 60fps frame budget. |
| **Spike 3** | CPU Compositing | 2-Track 1080p Alpha Blending | **17.4 FPS** (3.45s for 60 frames) | Software CPU compositing fails real-time 60fps target. |
| **Spike 4** | CPU Color Grading | 1080p Float32 CDL & 3D LUT | **5.0 FPS** (CPU vectorized) | Color correction must run in GPU fragment shaders. |
| **Spike 5** | Offline Audio DSP | 48kHz Stereo Summing & Peak/RMS | **1070x real-time** (4.67ms for 5s) | Audio processing on CPU has near-zero computational overhead. |
| **Spike 6** | Raw Video Export (Cold GPU) | 1080p60 Single Stream | NVENC = **93.2 FPS** (3.22s, cold GPU wake), x264 = **321.2 FPS** | Cold GPU initialization introduces ~1.5s latency; software x264 starts instantaneously. |
| **Spike 7** | Preview/Export Parity | 720p Test Gradient + Color Grade | **PSNR = 33.28 dB**, **MAE = 4.18 / 255** | Conformance verified; differences documented (integer truncation in filtergraph). |
| **Spike 8** | IPC Engine Comparison| 1080p 120-frame decode | Pipe = **49.2 FPS**, PyAV = **124.6 FPS** | **2.53x speedup** for direct C-bindings over subprocess pipe. |
| **Spike 9** | Bounded LRU Cache | 64 MB Budget (Holds ~7 frames) | Cold = **32.42 ms**, Warm = **0.003 ms** | Bounded memory budget strictly enforced (63.3 MB used); warm seek 10,000x faster. |
| **Spike 10**| Seek Cancellation | 10 Rapid Scrub Events | Cancelled = **9**, Executed = **1** | Monotonic generation tokens eliminate decode backlog during rapid scrubbing. |
| **Spike 11**| Real-Time Audio Timing| 256/512/1024 sample buffers | 256 samples (5.33ms): Mean = **0.020ms**, Headroom = **99.6%**, Underruns = **0/100** | Audio callback easily meets real-time deadlines with massive headroom. |
| **Spike 12**| Timeline Export (Warm GPU) | 2-Track + PiP Scale + Opacity + FX| NVENC = **173.9 FPS** (1.72s, warm GPU), x264 = **231.5 FPS** | Warm GPU execution achieves 173.9 FPS; filtergraph compositing drops CPU x264 from 321 to 231 FPS. |

---

## 3. Reconciled Benchmark Analysis: Cold vs Warm GPU States

In initial runs, Spike 6 reported 93.2 FPS for raw NVENC, whereas Spike 12 reported 173.9 FPS for full timeline NVENC. Detailed profiling revealed:
- **Cold Run Overhead**: On Windows laptop hardware with Optimus/dual-GPU, the first invocation of an NVENC process incurs a **~1.5 second initialization penalty** while the NVIDIA driver powers up the dGPU from low-power sleep state (P8 state to P0 state) and compiles CUDA/NVENC contexts. For a short 5-second test clip (300 frames), this 1.5s cold penalty reduces calculated throughput from ~180 FPS down to 93 FPS.
- **Warm Execution**: Once the GPU is in P0 performance state, both raw and multi-track NVENC consistently sustain **170 - 185 FPS** at 1080p60.
- **CPU x264 Degradation under Compositing**: Conversely, software `libx264` degrades from **321.2 FPS** (raw stream) down to **231.5 FPS** when adding multi-track scaling and overlay compositing, demonstrating CPU filtergraph overhead.

---

## 4. Test Data & Reproducible Commands

All test scripts and JSON logs are committed in the repository:
- Conformance test: `python spikes/parity_conformance_spike.py`
- Bounded cache & IPC test: `python spikes/bounded_cache_and_ipc_spike.py`
- Audio & export benchmark: `python spikes/audio_and_export_spike.py`
- Output metrics: `spikes/results.json`, `spikes/bounded_cache_results.json`, `spikes/audio_and_export_results.json`
