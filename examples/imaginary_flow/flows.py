"""A small imaginary experiment: prepare, simulate, post-process.

The three stages are plain ``@node`` functions.  ``pipeline`` submits them
in order, so each stage's output becomes the next stage's dependency edge.
Run it from the GUI with this file and ``plan.json``, or::

    flow-runner plan.json --module flows --flow pipeline

The model is deliberately simple: a first-order lag driven by a command
signal, compared against the measured reference in the raw data.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from sequence_extensions.flow import node


def _read_samples(raw_path: Path) -> list[dict[str, float]]:
    """Read the raw CSV and drop rows with non-numeric or missing fields."""
    samples: list[dict[str, float]] = []
    with raw_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                samples.append(
                    {
                        "time_s": float(row["time_s"]),
                        "command": float(row["command"]),
                        "measured": float(row["measured"]),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
    return sorted(samples, key=lambda sample: sample["time_s"])


@node
def prepare_data(raw_path: Path, out_dir: Path) -> Path:
    """Load the raw measurements, clean them, and write prepared data."""
    samples = _read_samples(Path(raw_path))
    if not samples:
        raise ValueError(f"no usable samples in {raw_path}")

    out_path = Path(out_dir) / "prepared.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"count": len(samples), "samples": samples}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_path


@node
def simulate(prepared_path: Path, gain: float = 0.8, damping: float = 0.8) -> Path:
    """Apply an imaginary first-order lag model to the prepared command."""
    prepared = json.loads(Path(prepared_path).read_text(encoding="utf-8"))
    alpha = min(1.0, max(0.01, 1.0 - damping))

    level = 0.0
    samples = []
    for sample in prepared["samples"]:
        level += (gain * sample["command"] - level) * alpha
        samples.append({**sample, "predicted": round(level, 6)})

    out_path = Path(prepared_path).with_name("simulation.json")
    out_path.write_text(
        json.dumps(
            {
                "model": {"gain": gain, "damping": damping, "alpha": alpha},
                "samples": samples,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return out_path


@node
def postprocess(sim_path: Path, threshold: float = 0.1) -> dict:
    """Compare prediction to measurement and write a small report."""
    simulation = json.loads(Path(sim_path).read_text(encoding="utf-8"))
    residuals = [sample["predicted"] - sample["measured"] for sample in simulation["samples"]]
    rmse = math.sqrt(sum(value * value for value in residuals) / len(residuals))
    max_error = max(abs(value) for value in residuals)

    report = {
        "count": len(residuals),
        "rmse": round(rmse, 6),
        "max_error": round(max_error, 6),
        "threshold": threshold,
        "passed": max_error <= threshold,
    }
    out_path = Path(sim_path).with_name("report.json")
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**report, "report": str(out_path)}


@node
def pipeline(raw_path: Path = "data/raw_measurements.csv", out_dir: Path = "_out") -> dict:
    """Run prepare -> simulate -> post-process and return the report."""
    prepared = prepare_data.submit(Path(raw_path), Path(out_dir))
    simulated = simulate.submit(prepared)
    return postprocess.submit(simulated)
