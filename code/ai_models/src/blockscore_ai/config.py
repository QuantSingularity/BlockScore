import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DEFAULT_MODEL_FILENAME = "credit_scoring_model.pkl"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    model_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("MODEL_PATH", str(ARTIFACTS_DIR / DEFAULT_MODEL_FILENAME))
        )
    )
    model_version: str = field(
        default_factory=lambda: os.getenv("MODEL_VERSION", "2.0.0")
    )
    api_key: str = field(default_factory=lambda: os.getenv("AI_MODEL_API_KEY", ""))
    host: str = field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("PORT", 5001))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    max_batch_size: int = field(default_factory=lambda: _env_int("MAX_BATCH_SIZE", 500))
    max_content_length: int = field(
        default_factory=lambda: _env_int("MAX_CONTENT_LENGTH", 4 * 1024 * 1024)
    )

    @property
    def metadata_path(self) -> Path:
        return self.model_path.with_suffix(".json")


def load_settings() -> Settings:
    return Settings()
