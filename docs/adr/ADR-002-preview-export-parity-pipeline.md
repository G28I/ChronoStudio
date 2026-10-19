# ADR-002: Preview and Export Parity Pipeline Architecture (Audited)

## Context
A critical failure mode in non-linear video editors is "Preview/Export Divergence" — where the rendered output differs from the playback preview due to differing blending equations, coordinate transformations, rounding rules, or color-space conversions.

## Clarified Parity Status & Empirical Evidence
1. **Initial Filtergraph Prototype**:
   - In `spikes/parity_conformance_spike.py`, we compared an in-memory 32-bit floating point shader simulation against an FFmpeg filtergraph approximation (`eq`, `colorlevels`, `colorchannelmixer`).
   - The test yielded **PSNR = 33.28 dB** and **MAE = 4.18 / 255** (~1.6% variance across dynamic range).
   - **Root Cause of Divergence**: The FFmpeg filtergraph path performs internal 8-bit fixed-point integer quantization and uses different transfer curves, whereas the shader preview runs in 32-bit IEEE 754 floating point.
2. **Definitive Parity Architecture**:
   - Approximate filtergraph translations are **insufficient** for professional color and compositing parity.
   - For complete preview/export parity, ChronoStudio's export pipeline must evaluate the **exact same compositing and effect evaluation engine** as the preview pipeline:
     - **Primary Export Path**: An offscreen rendering pipeline executing the identical GPU/shader rasterizer (or headless software rasterizer evaluating the exact same float32 formulas) writing rendered frames into the video encoder.
     - **Secondary Fallback**: FFmpeg filtergraph for simple single-track cuts without complex effects.

## Numerical Acceptance Tolerances (Phase 1 Exit Criteria)
For any clip or sequence evaluated across preview and export:
1. **Frame Duration & Count Parity**: **100% exact** (zero tolerance: $\Delta \text{frames} = 0$, $\Delta \text{PTS} = 0$).
2. **Transform & Positioning Parity**: Coordinate delta $\le 0.5\text{ pixels}$.
3. **Color & Blending Parity (Offscreen Render Path)**:
   - **PSNR $\ge 45.0\text{ dB}$** (perceptually lossless / visually identical).
   - **Max Absolute Error (MAE) $\le 1.0 / 255$**.
4. **Color & Blending Parity (FFmpeg Filtergraph Fallback Path)**:
   - **PSNR $\ge 30.0\text{ dB}$**.
   - **MAE $\le 6.0 / 255$**.

## Authoritative Effect Parameter Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ChronoStudioEffectParameters",
  "type": "object",
  "properties": {
    "transform": {
      "type": "object",
      "properties": {
        "position": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 },
        "scale": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 },
        "rotation": { "type": "number" },
        "anchor": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 },
        "opacity": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
      },
      "required": ["position", "scale", "rotation", "anchor", "opacity"]
    },
    "blend_mode": {
      "type": "string",
      "enum": ["Normal", "Multiply", "Screen", "Overlay", "Darken", "Lighten", "Add"]
    }
  },
  "required": ["transform", "blend_mode"]
}
```

## Consequences
- No unsubstantiated claims of "zero divergence" without empirical proof.
- Clear numeric thresholds separating acceptable encoding quantization from genuine compositing defects.
