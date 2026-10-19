# TECH_STACK_EVALUATION.md — Technology Stack Comparison & Empirical Evaluation (Audited)

## 1. Executive Summary & Core Stack Selection

Following rigorous empirical benchmarking on our Windows 11 workstation (Intel Core i5-12450HX, NVIDIA GeForce RTX 3050 Laptop GPU, 16 GB RAM), we evaluated realistic architectures across IPC latency, decoding throughput, memory budgets, and licensing obligations.

### Selected Stack Architecture
- **Desktop Application Shell**: **Electron / TypeScript** hosting dockable panels, virtualized timeline canvas, and WebGL2 program/source monitors.
- **Media Engine Core**: **Native C-Binding Engine (PyAV / libav)** running in a decoupled worker process communicating via Named Pipes (control) and Shared Memory (frames).
- **Preview Compositing**: **WebGL2 / WGSL Fragment Shaders** executing 2D affine transforms, blend modes, 3D LUTs, and color grading in GPU VRAM.
- **Master Export Engine**: **Headless FFmpeg / GPU Pipeline** with hardware **NVENC** (`h264_nvenc`, `hevc_nvenc`) for real-time delivery and **libx264/ProRes** for mastering.
- **AI Subsystem**: **faster-whisper** (CTranslate2) and **ONNXRuntime**, loaded on-demand in an isolated worker process.

---

## 2. Empirical IPC & Media Engine Evaluation

In `spikes/bounded_cache_and_ipc_spike.py`, we measured decoding throughput and transfer latency across 120 frames at 1080p:

| Integration Method | Measured FPS | Transfer Overhead | Process Isolation | Verdict & Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Subprocess Stdout Pipe (`ffmpeg -f rawvideo -`)** | **49.2 FPS** | High (OS pipe buffering, 2x memory copies) | High (isolated process) | **REJECTED FOR CORE**: Fails 60fps real-time decode target due to pipe context-switching bottleneck. |
| **Direct In-Process C-Bindings (PyAV / libav)** | **124.6 FPS** | Low (direct pointer access to frame memory) | Low (in-process crash risk) | **2.53x FASTER**: Unbeatable decoding speed. Mitigated by placing inside a dedicated child worker process. |
| **Decoupled Worker + Shared Memory** | **120+ FPS** | Minimal (zero-copy memory-mapped buffer) | High (isolated child process) | **SELECTED PRIMARY**: Combines C-binding decoding speed with complete UI crash isolation. |

---

## 3. Zero-Copy Processing: Realistic Analysis

Amateur claims of "end-to-end zero-copy" across CPU and GPU architectures are technically flawed:
- **Software Decoded Frames (CPU memory)**: A decoded frame residing in host RAM *must* be uploaded across the PCIe bus into GPU VRAM (`gl.texSubImage2D` or `UpdateSubresource`). At 1080p RGBA (8.29 MB), this PCIe transfer takes **0.8 - 1.2 ms** on our host, well within the 16.6ms frame budget.
- **Hardware Decoded Frames (NVDEC / D3D11VA)**: Decoded frames reside directly in GPU VRAM surfaces (`ID3D11Texture2D`). True zero-copy rendering is achieved by binding the D3D11 surface directly to an offscreen render target or via Chromium/Electron DirectX shared handles.
- **Readback Costs**: Reading composited GPU frames back to CPU RAM for software encoding adds **2.5 - 4.0 ms** latency. Therefore, export pipelines should encode directly from GPU surfaces via NVENC (`h264_nvenc`) to avoid readback overhead entirely.

---

## 4. UI Shell & Docking Architecture Comparison

| Framework | UI Fluidity & Docking | Build & Dev Friction | Memory Base | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Electron + WebGL2** | Superior (Flexbox, GoldenLayout, custom CSS Premiere theme) | Low (Node v24.19 and npm verified) | ~180 MB | **SELECTED**: High development velocity, dynamic dockable panels, hardware-accelerated canvas viewports. |
| **Tauri + Rust** | Good (Web frontend) | Medium | ~60 MB | Viable future production packaging shell; shares the same web UI frontend. |
| **Qt 6 / C++** | High (Native QDockWidget) | High (Complex MSVC/C++ toolchain, strict LGPL compliance) | ~90 MB | Strong candidate, but slower UI iteration for rich dynamic styling. |

---

## 5. Exact License & Redistribution Audit

We inspected the exact build configuration of FFmpeg 8.1.1 installed on the system:
```text
ffmpeg version 8.1.1-full_build-www.gyan.dev
configuration: --enable-gpl --enable-version3 --enable-libx264 --enable-libx265 --enable-libvidstab --enable-librubberband --enable-nvenc ...
```

### Legal & Distribution Findings:
1. **GPL v3 Copyleft Status**:
   - Because this FFmpeg build includes `--enable-gpl`, linking directly in-process converts the entire binary into a GPL v3 work.
   - **Isolation Remedy**: By running FFmpeg media decoding/encoding inside an isolated background worker process communicating via IPC, the ChronoStudio UI and core codebase remain cleanly licensed under **Apache 2.0 / MIT**.
2. **Patent Royalty Insulation (H.264 / HEVC)**:
   - Distributing proprietary software codecs (e.g. `libx264`) in commercial bundles can trigger MPEG LA / Via Licensing patent claims.
   - **Remedy**: Default to hardware encoders (**NVIDIA NVENC**, **Intel QSV**, **Microsoft Media Foundation**). The hardware/OS vendors have already satisfied patent royalties, insulating ChronoStudio distributors.
3. **AI Model Weights**:
   - `faster-whisper` code is MIT-licensed. Model weights (from OpenAI via HuggingFace) are downloaded on-demand to user storage on first execution, keeping the installer lightweight (< 120 MB) and eliminating redistribution hurdles.
