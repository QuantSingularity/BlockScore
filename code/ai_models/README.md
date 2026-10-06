# BlockScore AI Models

Credit scoring model, training pipeline, and HTTP service used by `code/backend`.

## Layout

| Path                                                                    | Purpose                                                                    |
| :---------------------------------------------------------------------- | :------------------------------------------------------------------------- |
| `src/blockscore_ai/config.py`                                           | Environment driven settings                                                |
| `src/blockscore_ai/api/`                                                | Flask app factory, routes, API key auth, JSON error handlers               |
| `src/blockscore_ai/scoring/`                                            | Feature extraction, rules, model registry, scoring service                 |
| `src/blockscore_ai/training/`                                           | Synthetic data, trainer, CLI, tabular preprocessing pipeline               |
| `src/blockscore_ai/research/`                                           | Ensemble model with fairness and SHAP, portfolio and credit risk analytics |
| `tests/unit/`, `tests/api/`, `tests/training/`, `tests/research/`       | Test suites mirroring the package                                          |
| `artifacts/`                                                            | Generated models, metadata, and reports (git ignored)                      |
| `wsgi.py`                                                               | Production entry point (`wsgi:app`)                                        |
| `pyproject.toml`                                                        | Package metadata, pytest, black, isort configuration                       |
| `requirements.txt`, `requirements-dev.txt`, `requirements-research.txt` | Runtime, development, and research dependencies                            |
| `Dockerfile`, `Makefile`                                                | Container image and common tasks                                           |

## Endpoints

| Method | Path             | Description                                           |
| :----- | :--------------- | :---------------------------------------------------- |
| GET    | `/health`        | Liveness and whether a trained model is loaded        |
| GET    | `/model-info`    | Model name, version, feature schema, training metrics |
| POST   | `/predict`       | Score one `creditHistory` list                        |
| POST   | `/batch-predict` | Score up to `MAX_BATCH_SIZE` histories                |

Each record in `creditHistory` has `timestamp`, `amount`, `repaid`, `repaymentTimestamp`, `recordType` (`loan` or `payment`), and `scoreImpact`.

Responses contain `score` (300 to 850), `confidence`, `factors`, `recordCount`, `modelName`, `modelVersion`, and `source` (`model`, `rules`, or `none`).

## Configuration

| Variable             | Default                              | Description                                 |
| :------------------- | :----------------------------------- | :------------------------------------------ |
| `PORT`               | `5001`                               | Listen port                                 |
| `HOST`               | `127.0.0.1`                          | Bind address (the container uses `0.0.0.0`) |
| `MODEL_PATH`         | `artifacts/credit_scoring_model.pkl` | Trained model artifact                      |
| `MODEL_VERSION`      | `2.0.0`                              | Version recorded when training              |
| `AI_MODEL_API_KEY`   | empty                                | When set, requests must send `X-API-Key`    |
| `MAX_BATCH_SIZE`     | `500`                                | Maximum items per batch request             |
| `MAX_CONTENT_LENGTH` | `4194304`                            | Maximum request body size in bytes          |
| `LOG_LEVEL`          | `INFO`                               | Logging level                               |

## Usage

| Task               | Command                                 |
| :----------------- | :-------------------------------------- |
| Install            | `make install`                          |
| Install dev tools  | `make install-dev`                      |
| Train              | `make train`                            |
| Serve (dev)        | `make serve`                            |
| Serve (production) | `gunicorn --bind 0.0.0.0:5001 wsgi:app` |
| Test               | `make test`                             |
| Lint               | `make lint`                             |
| Format             | `make format`                           |
| Research extras    | `make install-research`                 |

Without a trained artifact, or if its feature schema does not match, the service scores with the rule-based engine and reports `source: rules`. The backend calls this service through `AI_MODEL_URL` and falls back to its own rule-based engine if the service is unreachable.
