"""Consistent, checksummed database snapshots; validate before atomic restoration."""

import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path
from .model import DataError, utcnow, canonical_json
from .migrate import sha256_file
from .store import Store

MAX_DATABASE_BYTES = 5_000_000_000


def snapshot(store, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    errors = store.verify()
    if errors:
        raise DataError("Cannot snapshot invalid state: " + errors[0])
    with tempfile.TemporaryDirectory(prefix=".snapshot-", dir=directory) as tmp:
        database = Path(tmp) / "library.sqlite"
        packed = Path(tmp) / "library.sqlite.gz"
        store.backup(database)
        with Store(database) as consistent:
            if consistent.verify():
                raise DataError("Snapshot backup failed verification")
            total = consistent.count()
            baseline = consistent.db.execute(
                "SELECT count(*) FROM baseline"
            ).fetchone()[0]
            logical = consistent.logical_hash()
        with database.open("rb") as src, packed.open("wb") as target, gzip.GzipFile(
            filename="", mode="wb", fileobj=target, mtime=0, compresslevel=6
        ) as dst:
            for block in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(block)
        metadata = {
            "schema": 1,
            "created_at": utcnow(),
            "total": total,
            "baseline_total": baseline,
            "logical_hash": logical,
            "database_sha256": sha256_file(database),
            "compressed_sha256": sha256_file(packed),
            "database_bytes": database.stat().st_size,
            "compressed_bytes": packed.stat().st_size,
        }
        info = Path(tmp) / "snapshot.json"
        info.write_text(canonical_json(metadata))
        os.replace(packed, directory / "library.sqlite.gz")
        os.replace(info, directory / "snapshot.json")
    return metadata


def restore(directory, destination, *, minimum_total=63051):
    directory = Path(directory)
    destination = Path(destination)
    packed = directory / "library.sqlite.gz"
    meta = json.loads((directory / "snapshot.json").read_text())
    if (
        meta.get("schema") != 1
        or not isinstance(meta.get("total"), int)
        or meta["total"] < minimum_total
    ):
        raise DataError("Snapshot has unsupported schema or too few records")
    size = meta.get("database_bytes")
    if not isinstance(size, int) or not 0 < size <= MAX_DATABASE_BYTES:
        raise DataError("Invalid snapshot database size")
    if packed.stat().st_size != meta.get("compressed_bytes") or sha256_file(
        packed
    ) != meta.get("compressed_sha256"):
        raise DataError("Snapshot checksum mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".restore-", dir=destination.parent)
    os.close(fd)
    candidate = Path(name)
    try:
        written = 0
        with gzip.open(packed, "rb") as src, candidate.open("wb") as dst:
            while block := src.read(min(1024 * 1024, size - written + 1)):
                written += len(block)
                if written > size:
                    raise DataError("Decompressed snapshot exceeds declared size")
                dst.write(block)
            dst.flush()
            os.fsync(dst.fileno())
        if written != size or sha256_file(candidate) != meta.get("database_sha256"):
            raise DataError("Restored database checksum mismatch")
        with Store(candidate) as store:
            if (
                store.count() != meta["total"]
                or store.logical_hash() != meta.get("logical_hash")
                or store.db.execute("SELECT count(*) FROM baseline").fetchone()[0]
                != meta.get("baseline_total")
                or store.verify()
            ):
                raise DataError("Restored database failed integrity verification")
            store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        os.replace(candidate, destination)
        for suffix in ("-wal", "-shm"):
            Path(str(destination) + suffix).unlink(missing_ok=True)
        return meta
    except (OSError, EOFError) as e:
        raise DataError("Snapshot could not be decompressed") from e
    finally:
        candidate.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(str(candidate) + suffix).unlink(missing_ok=True)
