from __future__ import annotations

from pathlib import Path

from .canonical import build_canonical_json
from .chunking import generate_article_chunks
from .collectors import collect_norm_record
from .config import PipelineConfig
from .storage.files import save_pipeline_outputs
from .utils import build_session


def run_collection_pipeline(config: PipelineConfig) -> dict:
    session = build_session()
    record = collect_norm_record(config.urn, config.api_version, session)
    canonical_json = build_canonical_json(record, config.urn, pipeline_version=config.pipeline_version)
    chunks = generate_article_chunks(canonical_json)
    artifact_paths = save_pipeline_outputs(record, canonical_json, chunks, config.output_dir)

    return {
        "record": record,
        "canonical_json": canonical_json,
        "chunks": chunks,
        "artifacts": {key: str(path) for key, path in artifact_paths.items()},
        "output_dir": str(Path(config.output_dir).resolve()),
    }

