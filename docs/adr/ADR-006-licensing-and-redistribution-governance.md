# ADR-006: Licensing, Patent Boundaries, and Distribution Governance (Audited)

## Context
ChronoStudio aims to provide a free, independently implemented non-linear video editor. Shipping media tooling requires careful auditing of third-party licenses, patent royalties, and distribution boundaries.

## Audit of Installed Toolchains & Binaries
1. **FFmpeg 8.1.1 (Gyan.dev full build)**:
   - Configured with `--enable-gpl --enable-version3 --enable-libx264 --enable-libx265 --enable-libvidstab --enable-librubberband`.
   - **Legal Status**: This binary is explicitly licensed under **GPL v3**.
2. **PyAV (v18.1.0)**:
   - PyAV's wrapper code is licensed under BSD 2-Clause. However, because it dynamically binds to `avformat`, `avcodec`, `avutil` from the GPL FFmpeg build, any distributed bundle combining PyAV with this FFmpeg build is governed by **GPL v3**.
3. **Patent Pools (MPEG LA / Via Licensing for H.264 & HEVC)**:
   - While hardware acceleration (NVENC / QSV / AMF) offloads encoding to hardware chips whose manufacturers pay device royalties, container muxing (MP4), bitstream filtering, and distributing software wrappers may still be argued to require patent licensing in specific jurisdictions. Unsubstantiated claims of complete patent immunity are retracted. Commercial redistribution must undergo formal patent pool licensing review.
4. **Process Boundary Isolation**:
   - Decoupled processes communicate across named pipes and shared memory. While this cleanly separates memory spaces and prevents ABI/symbol contamination, distribution of a unified installer package containing both the UI shell and GPL binaries means the overall distributed product should be made available under **GPL v3** terms with complete source code availability.

## Decision
1. **Core Distribution Model**:
   - ChronoStudio will be released under the **GNU General Public License v3.0 (GPL v3)** to fully comply with all linked FFmpeg, PyAV, and x264/x265 obligations without ambiguity.
   - Original code authored for ChronoStudio will carry dual-licensing headers (Apache 2.0 / GPL v3) where appropriate to maximize component reuse.
2. **Codec Strategy**:
   - Primary default for playback and export: Hardware NVENC / NVDEC and native OS frameworks.
   - Software fallback: `libx264` (governed by GPL v3) and royalty-free formats (**ProRes**, **VP9**, **AV1**).
3. **AI Models**:
   - Model weights (e.g. OpenAI Whisper) are governed by MIT, but will be downloaded on-demand by the user rather than bundled in the application installer to minimize distribution liability and package size.

## Consequences
- Full, unambiguous legal compliance with GPL v3.
- No reliance on speculative legal exemptions regarding process separation or hardware patent pass-through.
