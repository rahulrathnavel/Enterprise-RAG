from __future__ import annotations

import sys

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.settings import load_settings, missing_required_secret_names
from src.ingestion.index_builder import build_index, ensure_demo_data


def main() -> int:
    """Prepare generated data and vector indexes before the web server starts.

    On public cloud platforms, API keys arrive at runtime as environment
    variables. Therefore the Docker image builds the deterministic SQLite/PDF/log
    demo data, while this startup hook builds the Qdrant index only after the
    NVIDIA secrets are available.
    """

    settings = load_settings()
    ensure_demo_data(settings)

    build_index_on_startup = os.getenv("BUILD_INDEX_ON_STARTUP", "true").strip().lower() in {"1", "true", "yes", "on"}
    if not build_index_on_startup:
        print("Runtime preparation generated data and skipped Qdrant indexing by configuration.")
        return 0

    missing = missing_required_secret_names(settings)
    if missing:
        print(
            "Runtime preparation skipped Qdrant indexing because required "
            f"environment variables are missing: {', '.join(missing)}"
        )
        print("The Streamlit UI will start and show a configuration error.")
        return 0

    counts = build_index(settings, force=True)
    print(f"Runtime preparation complete. Qdrant counts: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
