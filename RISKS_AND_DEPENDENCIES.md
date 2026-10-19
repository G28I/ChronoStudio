# RISKS_AND_DEPENDENCIES.md — Risk Register & Mitigation Strategy (Audited)

## 1. Legal, Licensing & Intellectual Property Risks

| Risk ID | Description | Severity | Likelihood | Mitigation Strategy (Audited) |
| :--- | :--- | :--- | :--- | :--- |
| Risk ID | Description | Severity | Likelihood | Mitigation Strategy (Audited) |
| :--- | :--- | :--- | :--- | :--- |
| **RISK-L01** | FFmpeg GPL v3 Licensing & Distribution | High | High | Bundled FFmpeg build (`--enable-gpl --enable-version3`) and PyAV dynamic bindings enforce **GNU General Public License v3.0 (GPL v3)** on the unified application distribution (ADR-006). Process isolation is for crash resilience and architectural cleanliness, not copyleft exemption. |
| **RISK-L02** | H.264 / HEVC Codec Patent Royalties | High | Medium | Shipping software H.264/HEVC encoders (`libx264/x265`) in commercial packages can trigger patent licensing claims. **Mitigation**: Default to hardware encoders (NVENC, QSV, AMF, Windows MediaFoundation) where patent royalties are already paid by hardware/OS vendors (ADR-006). |
| **RISK-L03** | Proprietary Adobe IP Contamination | Critical | Low | **Strict Clean-Room Policy**: Zero reverse-engineering of Adobe binaries; zero copying of proprietary Adobe assets. Rely purely on open industry specifications (OTIO, SMPTE 12M, ITU-R BS.1770, W3C WebVTT). |
| **RISK-L04** | AI Model Weight Redistribution | Medium | Low | Large Whisper weights are not bundled in the installer. Models are downloaded on-demand to user storage on first activation (ADR-006). |

---

## 2. Technical & Performance Risks

| Risk ID | Description | Severity | Likelihood | Mitigation Strategy (Audited) |
| :--- | :--- | :--- | :--- | :--- |
| **RISK-T01** | Long-GOP Scrub Latency & OOM Hazards | High | High | Bounded memory LRU cache strictly caps footprint at 63.3MB (ADR-004). Strict indexed cold seek target (< 30ms) is restored and met (18.17ms mean), and warm cache is 0.010ms. Obsolete seeks are cancelled via monotonic generation tokens. |
| **RISK-T02** | CPU Compositing Bottleneck | High | High | Verified in Spike 3 (software compositing failed at 17.4 FPS). **Mitigation**: Compositing, affine transforms, blend modes, and color grading are strictly offloaded to GPU fragment shaders (ADR-002). |
| **RISK-T03** | Preview vs Export Visual Divergence | High | Medium | Verified in Spike 7 (PSNR 33.28 dB due to integer truncation in filtergraph). **Mitigation**: Authoritative effect graph schema; master export uses offscreen GPU shader rendering where supported. |
| **RISK-T04** | Non-Integer Frame Rate Drift | High | High | Verified in `tests/test_time_model.py` (float division produces 1000.9999999999999). **Mitigation**: Exact `RationalTime` arithmetic and SMPTE 12M drop-frame standard (ADR-003). |
| **RISK-T05** | Variable Frame Rate (VFR) Audio Drift | High | Medium | Mobile video recordings often have VFR. **Mitigation**: Ingest pre-scanner detects VFR timestamps, normalizes PTS to fixed sequence timebase, and flags clips with jitter $> 0.5$ frames for background CFR transcoding. |
| **RISK-T06** | Audio Underrun on Heavy Load | Medium | Low | Verified in Spike 11 (256 samples has 99.6% headroom and 0 underruns). **Mitigation**: High-priority real-time audio thread using circular lock-free ring buffers. |
| **RISK-T07** | Desktop Port Collisions & Orphan Processes | High | Medium | Default ports 8080 or 8765 may conflict with running services. **Mitigation**: Electron main supervisor dynamically scans and binds available free ports (8081+); enforces process tree termination (`taskkill /pid PID /T /F`) with 0 orphan processes (tested in `tests/test_electron_shell.py`). |

