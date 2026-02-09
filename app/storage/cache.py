"""Simple JSON file cache for ML feedback and state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CACHE_DIR = Path(".cache")


class FileCache:
    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR) -> None:
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    def get(self, key: str) -> Any | None:
        p = self._path(key)
        if p.exists():
            return json.loads(p.read_text())
        return None

    def set(self, key: str, value: Any) -> None:
        self._path(key).write_text(json.dumps(value, default=str))

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()
