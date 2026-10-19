# REQUIREMENTS.md — Functional & Nonfunctional Specifications

## 1. Domain Coverage (A through L)

### Domain A: Media Ingest, Assets & Project Management
- **REQ-A1 (Universal Container Ingest)**: Ingest MP4, MOV, MKV, MXF, AVI, WebM, WAV, MP3, AAC, FLAC, AIFF, PNG, JPEG, TIFF, EXR, SVG.
- **REQ-A2 (Professional Metadata Extraction)**: Extract container & codec metadata: SMPTE timecode track, reel name, audio channel layout, color primaries, transfer matrix, bit depth, pixel aspect ratio, frame rate, GOP structure.
- **REQ-A3 (Hierarchical Project Bins)**: Folders/bins, smart search bins (filtering by codec, frame rate, resolution, label), color-coded labels, and drag-and-drop hierarchy.
- **REQ-A4 (Automated & On-Demand Proxies)**: Automated background proxy generation (ProRes 422 Proxy, DNxHR LB, low-bitrate H.264), 1-click proxy toggling without relinking.
- **REQ-A5 (Media Relinking & Offline Management)**: Automatic relative/absolute path relinking, batch directory reconnection, offline media warning indicators, and placeholder clip generators.

### Domain B: Timelines, Tracks & Frame-Accurate Editing
- **REQ-B1 (Arbitrary Multi-Track Sequences)**: Unlimited video and audio tracks, track lock, track mute/solo, track targeting, sync-locks.
- **REQ-B2 (Frame-Accurate Timebase)**: Support exact rational timebases (23.976, 24, 25, 29.97 DF/NDF, 30, 50, 59.94 DF/NDF, 60, 120 fps).
- **REQ-B3 (Full Trimming Toolset)**:
  - Selection Tool (`V`)
  - Ripple Edit Tool (`B`): Trims in/out point and shifts subsequent clips downstream.
  - Rolling Edit Tool (`N`): Adjusts edit point between adjacent clips without altering timeline total duration.
  - Rate Stretch Tool (`R`): Retimes clip duration visually.
  - Razor Tool (`C`): Slices clip at playhead or hovered frame.
  - Slip Tool (`Y`): Changes source in/out points while preserving clip timeline position and duration.
  - Slide Tool (`U`): Moves clip along timeline while rippling adjacent heads and tails.
  - Ripple Trim Previous/Next (`Q` / `W`): Ripple deletes head to playhead or tail from playhead.
- **REQ-B4 (Snapping & Magnetic Alignment)**: Snapping to playhead, clip boundaries, markers, in/out points, and track edges with configurable tolerance.
- **REQ-B5 (Nested Sequences & Multiclip Containers)**: Sequences placed inside parent sequences with recursive time evaluation and step-in editing.
- **REQ-B6 (Markers & Annotations)**: Sequence markers and clip markers with color coding, durations, comments, and chapter marks.

### Domain C: Playback Engine, Seeking & GPU Pipeline
- **REQ-C1 (Hardware-Accelerated Decoding)**: Automatic hardware decoder dispatch (NVIDIA NVDEC, Intel QSV, AMD AMF, DXVA2/D3D11VA).
- **REQ-C2 (Ring-Buffer Frame Cache)**: Forward and backward decoded frame cache ring-buffer to guarantee instant 0-latency J-K-L scrubbing.
- **REQ-C3 (Variable Playback Speeds)**: J-K-L jog/shuttle control supporting 1x, 2x, 4x, 8x, 16x forward/reverse speeds with pitch-compensated audio playback.
- **REQ-C4 (Fractional Playback Resolution)**: Full, 1/2, 1/4, 1/8 resolution preview downsampling for high-density 4K/6K/8K media playback.
- **REQ-C5 (Audio/Video Synchronization Guard)**: High-resolution hardware clock synchronization with audio master clock drift compensation (< 1ms AV drift).

### Domain D: Effects, Transitions & 2D/3D Compositing
- **REQ-D1 (Fixed Motion & Opacity Transforms)**: Position (X/Y), Scale (Uniform/Independent), Rotation, Anchor Point, Opacity, and 16 standard Blend Modes (Multiply, Screen, Overlay, etc.).
- **REQ-D2 (Bezier Keyframe System)**: Linear, Hold, Ease-In, Ease-Out, and custom Bezier spatial and temporal interpolation curves.
- **REQ-D3 (Video Transitions)**: Cross Dissolve, Dip to Black, Dip to White, Wipe, Slide, Iris, Zoom, Push with customizable curve transitions.
- **REQ-D4 (Compositing Masks & Matte)**: Pen tool bezier masking, ellipse/rectangle vector masks, inverted masks, mask feathering, mask expansion, and automatic 2D planar tracking.
- **REQ-D5 (Chroma Key & Green Screen)**: Color pick, tolerance, edge thinning, spill suppression, and alpha matte preview.
- **REQ-D6 (Optical Flow & Retiming)**: Frame blending and motion-vector optical flow interpolation for smooth slow-motion ramps.

### Domain E: Color Management & Scopes
- **REQ-E1 (3-Way Color Corrector / Lumetri Equivalency)**: Color wheels (Shadows/Lift, Midtones/Gamma, Highlights/Gain), Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Saturation, Temperature/Tint.
- **REQ-E2 (Curve Manipulation)**: Master RGB curve, individual R, G, B channels, Hue vs Saturation, Hue vs Hue, Hue vs Luma, Luma vs Saturation.
- **REQ-E3 (Real-Time Hardware Scopes)**:
  - Waveform Monitor (Luma, RGB Parade)
  - Vectorscope (Rec.709 75%/100% skin tone reference line)
  - Histogram (full 0-255/1024 distribution)
- **REQ-E4 (3D LUT Engine)**: Import, parse, and apply standard `.cube` (17x17x17 to 65x65x65) and `.3dl` LUTs with intensity sliders.
- **REQ-E5 (HDR & Wide Color Gamut)**: Rec.709, DCI-P3, Rec.2020, HLG, and PQ (HDR10) color profile handling with ACES / OpenColorIO color management pipeline.

### Domain F: Professional Audio Mixing & Processing
- **REQ-F1 (32-Bit Float Native Audio Engine)**: Full 32-bit floating-point multi-track bus summing with zero internal clipping.
- **REQ-F2 (Track & Clip Volume Automation)**: Rubber-band volume envelope editing directly on timeline tracks with bezier keyframes.
- **REQ-F3 (Parametric EQ & Dynamics)**: 4-band/8-band parametric equalizer, Compressor/Limiter, High/Low pass filters, Noise Gate.
- **REQ-F4 (Audio Noise Reduction)**: Spectral subtraction and local AI noise suppression.
- **REQ-F5 (Audio Scopes & Metering)**: True Peak meter, RMS meter, and LUFS EBU R128 loudness radar for broadcast compliance.
- **REQ-F6 (Voice-Over Direct Recording)**: Low-latency ASIO / WASAPI direct microphone recording onto armed timeline audio tracks.
- **REQ-F7 (Dual-System Audio Auto-Sync)**: Automatic waveform cross-correlation alignment to synchronize separate boom/lav mic audio to scratch camera audio.

### Domain G: Titles, Graphics & Captions
- **REQ-G1 (Rich Text & Vector Typography)**: Modern typography engine supporting system and custom TTF/OTF fonts, kerning, tracking, leading, stroke, multi-fill, drop shadows, and text alignment.
- **REQ-G2 (Subtitles & Open/Closed Captions)**: SRT, VTT, SubRip, and CEA-608/708 subtitle tracks aligned to timeline timecode.
- **REQ-G3 (Motion Graphic Templates)**: Parameterized graphic titles with in/out intro/outro responsive duration pinning.

### Domain H: Advanced Editorial & Workspaces
- **REQ-H1 (Multi-Camera Editing)**: Multi-camera source sequence creation (synced by timecode or audio waveform), 4-up/9-up multi-camera monitor with real-time angle switching.
- **REQ-H2 (Configurable Dockable Workspaces)**: Docking, tearing, floating panels (Timeline, Program Monitor, Source Monitor, Project Media, Audio Meters, Effects Control, Scopes).
- **REQ-H3 (Keyboard Shortcut Map Editor)**: Visual interactive keyboard layout editor with customizable shortcuts and Adobe Premiere Pro default preset.

### Domain I: Export & Delivery
- **REQ-I1 (Hardware-Accelerated Codecs)**: H.264 (NVENC, QSV, AMF), HEVC/H.265 (NVENC, QSV), AV1 (NVENC, QSV, SVT-AV1), Apple ProRes (422 HQ/LT/Proxy/4444), Avid DNxHD/DNxHR, VP9, WebM.
- **REQ-I2 (Broadcast & Web Presets)**: YouTube (1080p, 4K), Vimeo, Broadcast Rec.709, ProRes Master, Archive Master.
- **REQ-I3 (Batch Render Queue)**: Background render queue manager allowing editing while exports render in separate worker processes.
- **REQ-I4 (Export Quality Control)**: Check for black frames, audio clipping, missing media, and loudness compliance before final file write.

### Domain J: AI-Assisted Workflows
- **REQ-J1 (Local Speech-to-Text Transcription)**: Integrated local Whisper inference (via `faster-whisper` / `ctranslate2`) to generate word-level timestamps.
- **REQ-J2 (Text-Based Video Editing)**: Select text transcript to cut video clips directly on the timeline; delete filler words ("um", "uh") in one click.
- **REQ-J3 (Auto-Reframe / Smart Crop)**: Saliency and subject detection to dynamically pan 16:9 widescreen footage into 9:16 vertical social video.
- **REQ-J4 (Smart Scene Cut Detection)**: Detect cut boundaries in legacy flattened video files and automatically split them into timeline clips.

### Domain K: Interchange, Plugins & Automation
- **REQ-K1 (Industry Standard Interchange)**: Import and export OpenTimelineIO (`.otio`), Final Cut Pro XML (`.xml`), CMX 3600 EDL (`.edl`).
- **REQ-K2 (Plugin Extension API)**: Open C/C++ or WebAssembly effect plugin SDK for video filters and audio DSP.
- **REQ-K3 (Scripting & Headless Automation)**: CLI interface and JSON API to execute automated batch rendering and timeline generation headless.

### Domain L: Reliability, Project Persistence & System Health
- **REQ-L1 (Atomic Transactional Journaling)**: Every timeline edit is an atomic command (Command Pattern) with full Undo/Redo stack (depth >= 1000).
- **REQ-L2 (Zero-Data-Loss Continuous Autosave)**: Append-only transaction log ensures that a system crash loses at most seconds of work.
- **REQ-L3 (Project Serialization Schema)**: Human-readable, version-controlled project files (compressed JSON or SQLite relational bundle).
- **REQ-L4 (Crash Handler & Sandbox Isolation)**: Heavy decoding and rendering processes run in isolated worker processes so worker failures do not crash the primary UI.

---

## 2. Nonfunctional Requirements

| Category | Requirement | Target Specification |
| :--- | :--- | :--- |
| **Performance** | J-K-L Seek Latency | `< 30 ms` on indexed/proxy media |
| **Performance** | UI Framerate | 60 FPS constant UI render during active multi-track playback |
| **Performance** | Memory Footprint | Base footprint `< 350 MB`; dynamically bounded frame cache (configurable, e.g., 2 GB - 8 GB) |
| **Portability** | OS Support | Windows 10/11 (Primary Stage 0), Linux (Ubuntu/Fedora), macOS (Apple Silicon via Metal/MoltenVK) |
| **Reliability** | MTBF (Mean Time Between Failures) | `> 100 hours` continuous editing without fatal crash |
| **Security & Privacy**| Local Execution | 100% offline functionality; zero telemetry required; zero unauthorized network calls |
| **Licensing** | Code Base License | Open Source (MIT / Apache 2.0 / permissive GPL-compliant core) |
