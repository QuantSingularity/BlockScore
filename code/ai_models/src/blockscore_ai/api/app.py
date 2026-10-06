import logging
from typing import Optional

from blockscore_ai.api.errors import register_error_handlers
from blockscore_ai.api.routes import bp
from blockscore_ai.api.security import register_auth
from blockscore_ai.config import Settings, load_settings
from blockscore_ai.scoring import ModelRegistry, ScoringService
from flask import Flask


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
