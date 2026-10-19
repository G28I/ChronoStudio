# ADR-005: Transactional Persistence, Checksummed WAL, and Crash Recovery

## Context
Video editing sessions represent hours of creative labor. Periodic full-project saves (e.g., every 5 to 15 minutes) leave an unacceptable window of vulnerability where sudden power loss, OS crashes, or driver panics cause irreversible data loss. Conversely, unvalidated autosaves risk saving partially written, corrupt project files over good state.

## Empirical Evidence
- Unit tests in [`tests/test_crash_recovery.py`](file:///c:/Users/ramak/OneDrive/Desktop/RVideos/tests/test_crash_recovery.py):
  - Simulated sudden process termination during a write operation (torn trailing JSON write) was detected and recovered without crashing.
  - Checksum validation verified that tampered/corrupted records are rejected while preserving all prior valid transactions.
  - Replaying WAL records over an existing snapshot was proven strictly idempotent (no duplicated clips or track errors).

## Decision
1. **Atomic Project Snapshots**:
   - Project snapshots (`.cpj`) are written to a temporary sibling file (`.cpj.tmp`), flushed to disk via `fsync`, and atomically replaced via `os.replace` (POSIX `rename` / Win32 `MoveFileEx(MOVEFILE_REPLACE_EXISTING)`).
2. **Append-Only Write-Ahead Log (WAL)**:
   - Every mutating command generates a transaction record:
     `{ "tx_id": int, "cmd": string, "params": dict, "chk": string }`
   - `chk` is the truncated SHA-256 hash of `tx_id:cmd:params`.
   - The record is appended to `.cpj.wal` and immediately flushed before notifying the UI that the edit has completed.
3. **Idempotent Recovery Protocol**:
   - On startup or post-crash recovery, the engine loads the last valid `.cpj` snapshot.
   - It records `snapshot.last_applied_tx_id`.
   - It reads `.cpj.wal` sequentially, verifying each record's SHA-256 checksum. If a torn write is encountered at EOF, it truncates the torn bytes.
   - It applies only those records where `tx_id > snapshot.last_applied_tx_id`.
   - Once recovered, a new consolidated snapshot is saved, and the WAL is cleanly reset.

## Consequences
- Guaranteed zero-data-loss window reduced from minutes to sub-second transactions.
- Zero risk of project file corruption from sudden power loss or process kill.
