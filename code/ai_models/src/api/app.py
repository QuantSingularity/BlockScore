import logging
from typing import Optional

from flask import Flask
from src.api.errors import register_error_handlers
from src.api.routes import bp
from src.api.security import register_auth
from src.config import Settings, load_settings
from src.scoring import ModelRegistry, ScoringService


def create_app(
    settings: Optional[Settings] = None, registry: Optional[ModelRegistry] = None
) -> Flask:
    settings = settings or load_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    registry = registry or ModelRegistry(settings.model_path, settings.metadata_path)
    registry.load()

    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=settings.max_content_length,
        MAX_BATCH_SIZE=settings.max_batch_size,
        API_KEY=settings.api_key,
    )
    app.json.sort_keys = False
    app.extensions["scoring_service"] = ScoringService(registry)

    register_auth(app)
    register_error_handlers(app)
    app.register_blueprint(bp)
    return app
