# PROJECT.md — OpenPremiere (Codename: ChronoStudio)

## 1. Product Vision

**ChronoStudio** (working title: OpenPremiere) is an independently implemented, free, open-source, desktop-first professional non-linear video editing (NLE) platform. The project's core mission is to achieve broad functional parity with industry-standard professional suites (specifically Adobe Premiere Pro) across editing, multi-track compositing, 32-bit float audio mixing, advanced colour grading (Lumetri-class scopes and grading engines), motion graphics, hardware-accelerated delivery, and modern AI-assisted editorial workflows.

ChronoStudio is engineered to deliver:
- **Zero Subscription Lock-in**: Fully functional standalone desktop application with zero mandatory subscriptions, telemetry lock-in, or proprietary cloud dependencies.
- **Frame-Accurate Non-Destructive Core**: High-throughput media engine supporting mixed frame rates, anamorphic aspect ratios, deep color bit-depths (10-bit / 12-bit HDR), and strict rational timebase synchronization.
- **Modern Hardware Maximization**: Native GPU-accelerated decoding, effects evaluation, rendering, and encoding via NVENC/QSV/AMF, Vulkan/Direct3D 11/12, and multithreaded CPU pipelines.
- **Interoperability & Open Standards**: First-class support for OpenTimelineIO (OTIO), Final Cut Pro XML, CMX 3600 EDL, AAF, and universal media containers.

---

## 2. Target Users and Personas

| Persona | Role | Key Pain Points in Current Tools | ChronoStudio Value Proposition |
| :--- | :--- | :--- | :--- |
| **The Freelance Video Editor** | Commercials, YouTube, Corporate docs | High recurring Adobe subscription costs; sudden cloud licensing invalidation; project bloat | Identical high-velocity shortcut workflows (J-K-L, Ripple/Roll, Q/W ripple trims), zero recurring cost, fast startup. |
| **The Narrative Film & TV Assistant** | Feature films, episodic content, documentaries | Complex media relinking across team drives; interchange loss across tools; sync drift | Frame-accurate timecode matching, dual-system audio auto-sync, robust OTIO/EDL/XML roundtripping. |
| **The Motion & Color Specialist** | Grading, visual effects, title sequences | Sluggish playback on heavy timelines; lack of native GPU scopes; cumbersome roundtrips | Real-time GPU color pipeline (3D LUTs, ASC CDL, curves), integrated bezier masking, vector-accelerated text/shape engine. |
| **The Content Creator & Podcaster** | Multi-cam podcasts, social clips, explainers | Tedious manual cutting, transcription, and multi-cam line cutting | Built-in local Whisper speech-to-text, text-based editing, multi-cam live switching, auto-reframe for vertical video. |

---

## 3. Guiding Principles

1. **Non-Destructive Project Model**: Master media files are strictly immutable. Sequences represent directed acyclic graphs (DAGs) and clip reference trees evaluated dynamically at playback and export time.
2. **Deterministic Timebase & Frame Accuracy**: All timeline positioning, trimming, and duration calculations use exact rational arithmetic (`Rational(numerator, denominator)`) rather than floating-point time to eliminate timestamp drift.
3. **Clean-Room Independent Implementation**: ChronoStudio uses 100% original code and permissible open-source dependencies (MIT, Apache 2.0, BSD, LGPL 2.1/3.0, GPL with isolation where applicable). Zero reverse-engineering of proprietary binary code, zero circumventing of DRM or license managers, and zero copying of proprietary Adobe assets.
4. **Desktop-First & Local-First**: All editing, caching, project storage, rendering, and AI inferences run locally on the user's workstation. Cloud workflows (e.g., Frame.io style review) are optional extensions, not core requirements.
5. **Separation of Media Core and UI Presentation**: High-throughput media processing, audio mixing, and frame dispatch reside in a dedicated native core service/engine, decoupled from presentation rendering.
6. **Graceful Degradation & Proxy Automation**: Background proxy generation (ProRes Proxy / DNxHR LB / H.264 intra) guarantees smooth scrubbing on constrained hardware without altering master export fidelity.

---

## 4. Success Criteria & Quality Gates

### Quantitative Benchmarks
- **Scrub Latency**: Mean seek latency `< 25 ms` on intra-frame media and `< 45 ms` on standard Long-GOP H.264/HEVC (under proxy or cached indexing).
- **Playback Fluidity**: Zero dropped frames at 1080p60 and 4K30 on target mid-range hardware (e.g., Intel i5 + RTX 3050).
- **Audio Synchronization**: Sub-millisecond sample accuracy; `< 1` frame AV sync drift over 2 hours of playback.
- **Export Throughput**: `>= 1.5x` real-time at 1080p60 under NVENC/Hardware encoders and `>= 1.0x` real-time under high-quality CPU software encoders.
- **Crash Recovery & Data Integrity**: Continuous autosave journaling with recovery state loss `< 10` seconds in the event of an abnormal process termination.

### Qualitative Criteria
- Keyboard muscle memory compatibility: Standard Adobe Premiere Pro default shortcut set available as a first-class preset (`C` Razor, `V` Selection, `B` Ripple Edit, `N` Rolling Edit, `Y` Slip, `U` Slide, `Q`/`W` Ripple Trim).
- Professional interchange verification: Sequences roundtripped through DaVinci Resolve and Premiere Pro via FCPXML and OTIO without clip offset or timecode distortion.
