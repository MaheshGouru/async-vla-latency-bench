"""Output writers for requests, actions, episodes, and summaries."""

import csv
import json
from pathlib import Path
from typing import Any, Sequence


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    if not rows:
        path.write_text("")
        return
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_parquet(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required to write parquet outputs") from exc
    if not rows:
        pd.DataFrame().to_parquet(path, index=False)
        return
    df = pd.DataFrame(rows)
    df.to_parquet(path, index=False)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))
