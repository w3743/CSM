"""Simulate 60 days of memory decay at different use frequencies."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from brainmemory.models import Memory
from brainmemory.strength import ARCHIVE_THRESHOLD, current_strength, reinforce


DAYS = 60
INITIAL_STRENGTH = 0.6
INITIAL_DECAY_RATE = 0.02


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    color: str
    access_days: tuple[int, ...]


def every(interval: int, *, start: int = 1) -> tuple[int, ...]:
    return tuple(range(start, DAYS + 1, interval))


SCENARIOS = (
    Scenario("never", "Never (0x)", "#777777", ()),
    Scenario("once", "Once (1x)", "#a65628", (1,)),
    Scenario("monthly", "Every 30d (2x)", "#984ea3", every(30)),
    Scenario("biweekly", "Every 14d (5x)", "#ff7f00", every(14)),
    Scenario("weekly", "Weekly (9x)", "#377eb8", every(7)),
    Scenario("every_3d", "Every 3d (20x)", "#4daf4a", every(3)),
    Scenario("daily", "Daily (60x)", "#1a9641", every(1)),
)


def simulate() -> tuple[list[int], dict[str, list[float]], dict[str, list[float]]]:
    start = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    days = list(range(DAYS + 1))
    strengths: dict[str, list[float]] = {}
    decay_rates: dict[str, list[float]] = {}

    for scenario in SCENARIOS:
        memory = Memory(
            id=1,
            content=scenario.label,
            strength=INITIAL_STRENGTH,
            decay_rate=INITIAL_DECAY_RATE,
            trust=0.5,
            created_at=start,
            updated_at=start,
            last_accessed_at=start,
        )
        scenario_strengths = [INITIAL_STRENGTH]
        scenario_decay_rates = [INITIAL_DECAY_RATE]

        for day in range(1, DAYS + 1):
            now = start + timedelta(days=day)
            if day in scenario.access_days:
                memory.strength = reinforce(memory, now=now)
                memory.last_accessed_at = now
                memory.access_count += 1
            scenario_strengths.append(current_strength(memory, now=now))
            scenario_decay_rates.append(memory.decay_rate)

        strengths[scenario.key] = scenario_strengths
        decay_rates[scenario.key] = scenario_decay_rates

    return days, strengths, decay_rates


def write_csv(
    output_dir: Path,
    days: list[int],
    strengths: dict[str, list[float]],
    decay_rates: dict[str, list[float]],
) -> None:
    with (output_dir / "decay_60d.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["day", *[f"{s.key}_R" for s in SCENARIOS], *[f"{s.key}_decay" for s in SCENARIOS]])
        for index, day in enumerate(days):
            writer.writerow([
                day,
                *[f"{strengths[s.key][index]:.6f}" for s in SCENARIOS],
                *[f"{decay_rates[s.key][index]:.6f}" for s in SCENARIOS],
            ])


def plot_curves(output_dir: Path, days: list[int], strengths: dict[str, list[float]]) -> None:
    fig, ax = plt.subplots(figsize=(13, 6.2))
    for scenario in SCENARIOS:
        ax.plot(
            days,
            strengths[scenario.key],
            color=scenario.color,
            linewidth=2.2,
            label=scenario.label,
        )
        for access_day in scenario.access_days:
            ax.scatter(
                access_day,
                strengths[scenario.key][access_day],
                color=scenario.color,
                s=10,
                alpha=0.65,
            )

    ax.axhline(
        ARCHIVE_THRESHOLD,
        color="#b2182b",
        linestyle="--",
        linewidth=1,
        label=f"Archive threshold ({ARCHIVE_THRESHOLD:.1f})",
    )
    ax.set(title="60-Day Memory Decay by Use Frequency", xlabel="Day", ylabel="Memory strength R")
    ax.set_xlim(0, DAYS)
    ax.set_ylim(0, 1.02)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9)
    fig.tight_layout()
    fig.savefig(output_dir / "decay_60d_curves.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_heatmap(output_dir: Path, strengths: dict[str, list[float]]) -> None:
    data = np.asarray([strengths[scenario.key] for scenario in SCENARIOS])
    fig, ax = plt.subplots(figsize=(14, 4.8))
    image = ax.imshow(data, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
    ax.set_yticks(range(len(SCENARIOS)), labels=[scenario.label for scenario in SCENARIOS])
    ax.set_xticks(range(0, DAYS + 1, 5))
    ax.set_xticklabels(range(0, DAYS + 1, 5))
    ax.set(title="60-Day Strength Heatmap", xlabel="Day")
    for row in range(len(SCENARIOS)):
        for day in (0, 7, 14, 30, 45, 60):
            value = data[row, day]
            ax.text(day, row, f"{value:.2f}", ha="center", va="center",
                    fontsize=7, color="white" if value < 0.45 else "black")
    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Memory strength R")
    fig.tight_layout()
    fig.savefig(output_dir / "decay_60d_heatmap.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_summary(output_dir: Path, strengths: dict[str, list[float]], decay_rates: dict[str, list[float]]) -> None:
    checkpoints = (7, 14, 30, 45, 60)
    lines = [
        "# 60-day memory decay simulation",
        "",
        f"Initial strength: {INITIAL_STRENGTH}; initial decay rate: {INITIAL_DECAY_RATE}.",
        "Dots in the curve chart indicate successful uses/retrievals.",
        "",
        "| Frequency | Uses | Day 7 | Day 14 | Day 30 | Day 45 | Day 60 | Final decay |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in SCENARIOS:
        values = strengths[scenario.key]
        lines.append(
            f"| {scenario.label} | {len(scenario.access_days)} | "
            + " | ".join(f"{values[day]:.3f}" for day in checkpoints)
            + f" | {decay_rates[scenario.key][-1]:.5f} |"
        )
    (output_dir / "decay_60d_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    output_dir = Path(__file__).resolve().parent / "sim_charts"
    output_dir.mkdir(parents=True, exist_ok=True)
    days, strengths, decay_rates = simulate()
    write_csv(output_dir, days, strengths, decay_rates)
    plot_curves(output_dir, days, strengths)
    plot_heatmap(output_dir, strengths)
    write_summary(output_dir, strengths, decay_rates)

    print("60-day simulation complete")
    for scenario in SCENARIOS:
        print(
            f"{scenario.label:16s} uses={len(scenario.access_days):2d} "
            f"R60={strengths[scenario.key][-1]:.3f} "
            f"decay={decay_rates[scenario.key][-1]:.5f}"
        )


if __name__ == "__main__":
    main()
