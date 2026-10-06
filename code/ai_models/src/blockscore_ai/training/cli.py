import argparse
import logging
from pathlib import Path
from typing import Optional, Sequence

from blockscore_ai.config import load_settings
from blockscore_ai.training.synthetic import generate_synthetic_data
from blockscore_ai.training.trainer import (
    evaluate_model,
    save_model,
    split_data,
    train_model,
)


def main(argv: Optional[Sequence[str]] = None) -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(prog="blockscore_ai.training")
    parser.add_argument("--samples", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=settings.model_path)
    parser.add_argument("--model-version", default=settings.model_version)
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    data = generate_synthetic_data(n_samples=args.samples, seed=args.seed)
    X_train, X_test, y_train, y_test = split_data(data, seed=args.seed)
    model = train_model(X_train, y_train, seed=args.seed)
    metrics = evaluate_model(model, X_test, y_test)
    save_model(model, metrics, args.output, args.model_version)
