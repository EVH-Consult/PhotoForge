from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def compute_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()

    with path.open("rb") as file_handle:
        while True:
            chunk = file_handle.read(CHUNK_SIZE)
            if not chunk:
                break
            sha256.update(chunk)

    return sha256.hexdigest()


def derive_short_hash(sha256_hex: str) -> str:
    return sha256_hex[:8]


def hash_file(path: Path) -> tuple[str, str]:
    sha256_hex = compute_sha256(path)
    short_hash = derive_short_hash(sha256_hex)
    return sha256_hex, short_hash

def ordered_hashes(paths, workers=1, *, hash_function=compute_sha256):
    """Yield full hashes/errors in input order with at most 2*workers futures.

    No result persists beyond this invocation. Paths must belong to one stable
    caller-owned snapshot; file size/mtime never substitutes for full hashing.
    """
    from collections import deque
    from concurrent.futures import ThreadPoolExecutor

    def outcome(path):
        try:
            return hash_function(path)
        except Exception as exc:
            return exc

    if workers == 1:
        for path in paths:
            yield outcome(path)
        return
    with ThreadPoolExecutor(max_workers=workers) as executor:
        source = iter(paths)
        pending = deque()
        for _ in range(workers * 2):
            path = next(source, None)
            if path is None:
                break
            pending.append(executor.submit(outcome, path))
        while pending:
            yield pending.popleft().result()
            path = next(source, None)
            if path is not None:
                pending.append(executor.submit(outcome, path))
