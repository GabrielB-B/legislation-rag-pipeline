from __future__ import annotations

from pathlib import Path
import json
import re

from ..utils import ensure_directory, slugify_urn


def write_json(path: str | Path, payload) -> Path:
    target = Path(path)
    ensure_directory(target.parent)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def write_jsonl(path: str | Path, rows: list[dict]) -> Path:
    target = Path(path)
    ensure_directory(target.parent)
    with target.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    return target


def save_pipeline_outputs(record: dict, canonical_json: dict, chunks: list[dict], output_dir: str | Path) -> dict[str, Path]:
    output = ensure_directory(output_dir)
    number = canonical_json["canonical"].get("numero") or "norma"
    number_slug = re.sub(r"[^0-9A-Za-z]+", "_", str(number)).strip("_") or "norma"
    urn_slug = slugify_urn(record["urn"])

    paths = {
        "record": write_json(output / f"{urn_slug}_registro_norma.json", record),
        "canonical": write_json(output / f"norma_canonica_{number_slug}.json", canonical_json),
        "chunks_json": write_json(output / f"norma_chunks_{number_slug}.json", chunks),
        "chunks_jsonl": write_jsonl(output / f"norma_chunks_{number_slug}.jsonl", chunks),
    }
    return paths

