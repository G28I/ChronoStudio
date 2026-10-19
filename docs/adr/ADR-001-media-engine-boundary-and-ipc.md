# ADR-001: Media Engine Subsystem Boundaries and IPC Architecture (Audited)

## Context
A professional non-linear video editor requires separating UI responsiveness from computationally intensive media operations (frame demuxing, video decoding, audio DSP mixing, GPU shader compositing, and export encoding).

## Implemented Architecture vs. Future Roadmap
1. **Actual Implementation (Phase 1 Verified)**:
   - **Standalone Desktop Shell**: Electron 44 desktop wrapper with `nodeIntegration: false`, `contextIsolation: true`, and `sandbox: true`. Preload script exposes safe, scoped IPC via `contextBridge` (`window.electronAPI`).
   - **Process Supervision**: Electron main process supervises the Python backend host and Media Engine worker processes.
   - **Port Collision Resolution**: Dynamically probes and binds free TCP ports (resolving default port 8080/8765 collisions automatically to 8081+).
   - **Clean Termination**: Enforces complete process tree termination on window close (`taskkill /pid PID /T /F` on Windows) with zero orphaned child processes.
   - **IPC Protocol**: Localhost TCP loopback socket (`127.0.0.1:8765`) with newline-delimited JSON-RPC messages.
   - **Control Plane**: Bi-directional asynchronous request/response supporting monotonic generation-token seek cancellation (`generation_id`), stream import, clip editing, and export triggering.
   - **Verified in Tests**: Automated integration suites [`tests/test_worker_ipc.py`](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/tests/test_worker_ipc.py) and [`tests/test_electron_shell.py`](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/tests/test_electron_shell.py).
2. **Future Optimization (Phase 2/3 Roadmap)**:
   - For high-bitrate uncompressed 4K video preview, Windows Named Pipes (`\\.\pipe\chronostudio-ipc`) and Windows Shared Memory (`CreateFileMapping` / `OpenFileMapping`) will replace TCP JSON-RPC for bulk frame pixel buffer transfers to eliminate loopback network stack overhead.

## Component Boundaries & Process Model
- **UI Shell**: Owns virtualized timeline canvas, dockable workspaces, command history, and presentation canvas management. Zero video decoding or audio DSP occurs on the UI thread.
- **Dedicated Native Media Engine Worker**: Out-of-process worker process running in-process C-bindings (`libavformat`, `libavcodec`). Owns decoded frame buffers, PTS scheduling, and audio mixing bus.
- **Seek Cancellation**: Monotonic integer generation tokens (`generation_id`) are checked prior to demuxing/decoding. Stale seek requests are aborted immediately, dropping obsolete frames during rapid scrubbing.
- **Crash Isolation**: Worker termination or crash does not bring down the UI shell; the Electron supervisor catches child exit signals, logs crash telemetry, alerts the UI, and offers automatic restart.

## Consequences
- Honest documentation matching working code: Phase 1 relies on verified TCP JSON-RPC and standalone Electron supervision.
- Zero-copy claims are strictly bounded: intra-process frame handling avoids intermediate serialization, but bulk video frame transfer over TCP currently carries memory copy overhead.
