"""
core/transactional_journal.py — Crash-Resistant Transactional Project Persistence
Implements atomic snapshots, append-only WAL with SHA256 integrity checksums,
idempotent recovery replay, and torn-write corruption resistance.
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional


class TransactionRecord:
    def __init__(self, tx_id: int, cmd: str, params: Dict[str, Any], checksum: Optional[str] = None):
        self.tx_id = tx_id
        self.cmd = cmd
        self.params = params
        self.checksum = checksum or self.compute_checksum()

    def compute_checksum(self) -> str:
        body = f"{self.tx_id}:{self.cmd}:{json.dumps(self.params, sort_keys=True)}"
        return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]

    def verify(self) -> bool:
        return self.checksum == self.compute_checksum()

    def to_json(self) -> str:
        return json.dumps({
            "tx_id": self.tx_id,
            "cmd": self.cmd,
            "params": self.params,
            "chk": self.checksum
        })

    @classmethod
    def from_json(cls, line: str) -> "TransactionRecord":
        d = json.loads(line)
        rec = cls(d["tx_id"], d["cmd"], d["params"], d["chk"])
        if not rec.verify():
            raise ValueError(f"Corrupted transaction record at tx_id={rec.tx_id}")
        return rec


class ProjectModel:
    """In-memory model of project state."""
    def __init__(self, project_id: str = "proj_001"):
        self.project_id = project_id
        self.last_applied_tx_id = 0
        self.tracks: Dict[str, List[Dict[str, Any]]] = {"V1": [], "A1": []}

    def apply_command(self, cmd: str, params: Dict[str, Any]) -> None:
        if cmd == "ADD_CLIP":
            track = params.get("track", "V1")
            self.tracks.setdefault(track, []).append({
                "clip_id": params["clip_id"],
                "asset_id": params["asset_id"],
                "start": params["start"],
                "duration": params["duration"]
            })
        elif cmd == "DELETE_CLIP":
            clip_id = params["clip_id"]
            for trk in self.tracks.values():
                trk[:] = [c for c in trk if c["clip_id"] != clip_id]
        elif cmd == "TRIM_CLIP":
            clip_id = params["clip_id"]
            for trk in self.tracks.values():
                for c in trk:
                    if c["clip_id"] == clip_id:
                        c["duration"] = params["new_duration"]
        else:
            raise ValueError(f"Unknown command: {cmd}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "last_applied_tx_id": self.last_applied_tx_id,
            "tracks": self.tracks
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectModel":
        model = cls(data["project_id"])
        model.last_applied_tx_id = data.get("last_applied_tx_id", 0)
        model.tracks = data.get("tracks", {"V1": [], "A1": []})
        return model


class TransactionalPersistenceEngine:
    def __init__(self, project_file: str):
        self.project_file = os.path.abspath(project_file)
        self.wal_file = f"{self.project_file}.wal"

    def write_atomic_snapshot(self, model: ProjectModel) -> None:
        """Writes snapshot atomically via temp file + os.replace."""
        temp_path = f"{self.project_file}.tmp"
        data = model.to_dict()
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, self.project_file)

    def log_transaction(self, tx_id: int, cmd: str, params: Dict[str, Any]) -> None:
        """Appends verified transaction to WAL."""
        rec = TransactionRecord(tx_id, cmd, params)
        with open(self.wal_file, "a", encoding="utf-8") as f:
            f.write(rec.to_json() + "\n")
            f.flush()
            os.fsync(f.fileno())

    def recover(self) -> ProjectModel:
        """
        Loads base snapshot, replays subsequent valid WAL records idempotently.
        Gracefully handles trailing torn writes or corruption.
        """
        if os.path.exists(self.project_file):
            with open(self.project_file, "r", encoding="utf-8") as f:
                model = ProjectModel.from_dict(json.load(f))
        else:
            model = ProjectModel()

        if not os.path.exists(self.wal_file):
            return model

        valid_records: List[TransactionRecord] = []
        with open(self.wal_file, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = TransactionRecord.from_json(line)
                    valid_records.append(rec)
                except Exception:
                    # Torn write or corruption at end of log during crash
                    break

        for rec in valid_records:
            if rec.tx_id > model.last_applied_tx_id:
                model.apply_command(rec.cmd, rec.params)
                model.last_applied_tx_id = rec.tx_id

        return model
