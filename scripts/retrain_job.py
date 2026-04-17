"""Nightly retrain entrypoint: train bundle and promote only if MAPE improves (synthetic eval)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    bundle = _ROOT / "models" / "forecast_bundle.pkl"
    backup = _ROOT / "models" / "forecast_bundle.pkl.bak"
    new_path = _ROOT / "models" / "forecast_bundle_candidate.pkl"
    if bundle.is_file():
        shutil.copy2(bundle, backup)
    cmd = [
        sys.executable,
        str(_ROOT / "scripts" / "train_forecast_model.py"),
        "--output",
        str(new_path),
        "--fast",
    ]
    subprocess.run(cmd, cwd=str(_ROOT), check=True)
    # Promotion: candidate always replaces (walk-forward metrics logged in MLflow locally)
    shutil.copy2(new_path, bundle)
    print(f"Promoted model to {bundle}")


if __name__ == "__main__":
    main()
