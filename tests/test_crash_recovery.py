"""
tests/test_crash_recovery.py — Unit Tests for Transactional Crash Recovery
"""

import os
import pytest
from core.transactional_journal import ProjectModel, TransactionalPersistenceEngine, TransactionRecord


@pytest.fixture
def test_env(tmp_path):
    proj_path = tmp_path / "test_project.cpj"
    engine = TransactionalPersistenceEngine(str(proj_path))
    return engine, proj_path


def test_clean_snapshot_and_recovery(test_env):
    engine, _ = test_env
    model = ProjectModel("proj_clean")
    model.apply_command("ADD_CLIP", {"clip_id": "c1", "asset_id": "a1", "start": 0, "duration": 100})
    model.last_applied_tx_id = 1
    engine.write_atomic_snapshot(model)

    recovered = engine.recover()
    assert recovered.project_id == "proj_clean"
    assert recovered.last_applied_tx_id == 1
    assert len(recovered.tracks["V1"]) == 1
    assert recovered.tracks["V1"][0]["clip_id"] == "c1"


def test_wal_replay_and_idempotence(test_env):
    engine, _ = test_env
    # 1. Base snapshot with tx_id = 2
    model = ProjectModel("proj_wal")
    model.apply_command("ADD_CLIP", {"clip_id": "c1", "asset_id": "a1", "start": 0, "duration": 100})
    model.apply_command("ADD_CLIP", {"clip_id": "c2", "asset_id": "a2", "start": 100, "duration": 50})
    model.last_applied_tx_id = 2
    engine.write_atomic_snapshot(model)

    # 2. Append WAL records: tx 1 (duplicate/older), tx 2 (duplicate), tx 3 (new), tx 4 (new)
    engine.log_transaction(1, "ADD_CLIP", {"clip_id": "c1", "asset_id": "a1", "start": 0, "duration": 100})
    engine.log_transaction(2, "ADD_CLIP", {"clip_id": "c2", "asset_id": "a2", "start": 100, "duration": 50})
    engine.log_transaction(3, "ADD_CLIP", {"clip_id": "c3", "asset_id": "a3", "start": 150, "duration": 75})
    engine.log_transaction(4, "TRIM_CLIP", {"clip_id": "c3", "new_duration": 60})

    recovered = engine.recover()
    # tx 1 and 2 must NOT duplicate c1 or c2
    assert len(recovered.tracks["V1"]) == 3
    assert recovered.last_applied_tx_id == 4
    c3 = next(c for c in recovered.tracks["V1"] if c["clip_id"] == "c3")
    assert c3["duration"] == 60


def test_crash_with_torn_write_recovery(test_env):
    engine, _ = test_env
    model = ProjectModel("proj_torn")
    model.last_applied_tx_id = 1
    model.apply_command("ADD_CLIP", {"clip_id": "c1", "asset_id": "a1", "start": 0, "duration": 100})
    engine.write_atomic_snapshot(model)

    # Valid transaction 2
    engine.log_transaction(2, "ADD_CLIP", {"clip_id": "c2", "asset_id": "a2", "start": 100, "duration": 100})

    # Simulate power cut / sudden kill during write of transaction 3 (incomplete JSON line)
    with open(engine.wal_file, "a", encoding="utf-8") as f:
        f.write('{"tx_id": 3, "cmd": "ADD_CLIP", "params": {"clip_id": "c3", "asse')

    recovered = engine.recover()
    # Must cleanly recover up to tx 2, cleanly discarding the torn write without crashing
    assert recovered.last_applied_tx_id == 2
    assert len(recovered.tracks["V1"]) == 2
    assert recovered.tracks["V1"][1]["clip_id"] == "c2"


def test_checksum_corruption_detection(test_env):
    engine, _ = test_env
    # Valid transaction
    engine.log_transaction(1, "ADD_CLIP", {"clip_id": "c1", "asset_id": "a1", "start": 0, "duration": 100})
    
    # Tamper with the transaction payload without updating checksum
    with open(engine.wal_file, "r") as f:
        line = f.readline()
    tampered_line = line.replace('"start": 0', '"start": 9999')
    with open(engine.wal_file, "w") as f:
        f.write(tampered_line)

    # Recovery must reject the tampered line due to checksum mismatch
    recovered = engine.recover()
    assert recovered.last_applied_tx_id == 0
    assert len(recovered.tracks["V1"]) == 0
