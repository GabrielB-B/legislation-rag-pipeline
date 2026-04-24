from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class PostgresConfig:
    host: str = "localhost"
    port: int = 5432
    dbname: str = "lexml_juridico"
    user: str = "postgres"
    password: str = "postgres"

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        return cls(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "lexml_juridico"),
            user=os.getenv("PGUSER", "postgres"),
            password=os.getenv("PGPASSWORD", "postgres"),
        )

    def as_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
        }


@dataclass(slots=True)
class EmbeddingConfig:
    model_name: str = "intfloat/multilingual-e5-small"
    text_field: str = "texto_contextualizado"
    metric: str = "cosine_distance"
    normalize: bool = True


@dataclass(slots=True)
class PipelineConfig:
    urn: str
    api_version: int = 3
    output_dir: str = "artifacts"
    pipeline_version: str = "v1"

